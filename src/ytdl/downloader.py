"""Execução dos downloads: prévia, vídeo/áudio, conversão, cancelamento e limpeza."""

import json
import logging
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import uuid
from collections import deque
from dataclasses import replace
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from ytdl.clip import Clip, clip_suffix
from ytdl.commands import audio_args, ffmpeg_args, info_args, playlist_args, preview_args, video_args
from ytdl.errors import NO_SPACE, Cancelled, DownloadError, error_for_live, friendly_error
from ytdl.formats import VideoInfo, VideoPlan, available_heights, best_audio, parse_info
from ytdl.net import urlopen
from ytdl.paths import destination_path
from ytdl.playlist import Playlist, parse_playlist, playlist_limit
from ytdl.titles import clean_title
from ytdl.progress import DownloadTracker, Progress, parse_dl_line, parse_ffmpeg_line
from ytdl.tools import NO_WINDOW, Tools, run_quiet

log = logging.getLogger("ytdl")
DELIVER_LOCK = threading.Lock()
TAIL_LINES = 50
INFO_MAX_AGE_S = 3 * 3600  # depois disso, consulta de novo


class ProcessRunner:
    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def run(self, args: list[str], on_line: Callable[[str], None]) -> int:
        with self._lock:
            self._proc = subprocess.Popen(
                [str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace", creationflags=NO_WINDOW,
            )
        for line in self._proc.stdout:
            on_line(line.rstrip("\r\n"))
        return self._proc.wait()

    def cancel(self) -> None:
        with self._lock:
            proc = self._proc
        if proc and proc.poll() is None:
            # /T derruba também o ffmpeg que o yt-dlp abriu
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                           capture_output=True, creationflags=NO_WINDOW)


def fetch_info(t: Tools, url: str, run=run_quiet) -> VideoInfo:
    args = info_args(t, url)
    log.info("info: %s", args)
    result = run(args, timeout=180)
    if result.returncode != 0:
        log.error("info falhou: %s", result.stderr[-4000:])
        raise DownloadError(friendly_error(result.stderr))
    data = json.loads(result.stdout)
    live = error_for_live(data.get("live_status"))
    if live:
        raise DownloadError(live)
    info = parse_info(data)
    if not available_heights(info) or not info.audio_formats:
        raise DownloadError(friendly_error(""))
    return info


OEMBED_URL = "https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v={}"


def fetch_oembed(video_id: str, opener=urlopen) -> tuple[str, str] | None:
    """Título e canal pela consulta leve do YouTube (não conta como extração do yt-dlp).

    None quando não dá para saber por aqui (vídeo com incorporação bloqueada, sem rede…).
    """
    try:
        with opener(OEMBED_URL.format(video_id), timeout=15) as resp:
            data = json.loads(resp.read())
        return data["title"], data.get("author_name") or "Desconhecido"
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 404):
            raise DownloadError(friendly_error("video unavailable")) from exc
        return None
    except (OSError, ValueError, KeyError):
        return None


def fetch_playlist(t: Tools, url: str, playlist_id: str, run=run_quiet) -> Playlist:
    limit = playlist_limit(playlist_id)
    args = playlist_args(t, url, limit)
    log.info("playlist: %s", args)
    result = run(args, timeout=300)
    if result.returncode != 0:
        log.error("playlist falhou: %s", result.stderr[-4000:])
        raise DownloadError(friendly_error(result.stderr))
    return parse_playlist(json.loads(result.stdout), limit)


def _part(size: int, clip: Clip | None, duration: int) -> int:
    """Tamanho proporcional ao trecho (para conferir o espaço livre)."""
    if not clip or not duration:
        return size
    return size * (clip[1] - clip[0]) // duration


def cleanup_stale_temp(tmp_root: Path) -> None:
    if tmp_root.exists():
        for child in tmp_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)


class Job:
    def __init__(self, tools: Tools, tmp_root: Path, on_progress: Callable[[Progress], None],
                 runner_factory: Callable[[], ProcessRunner] = ProcessRunner,
                 free_space: Callable[[Path], int] = lambda p: shutil.disk_usage(p).free):
        self.tools = tools
        self.tmp_root = tmp_root
        self.on_progress = on_progress
        self.runner_factory = runner_factory
        self.free_space = free_space
        self._cancelled = False
        self._runner: ProcessRunner | None = None

    # --- API pública -------------------------------------------------

    def run_video(self, url: str, info: VideoInfo, plan: VideoPlan, base_dir: Path, clip: Clip | None = None) -> Path:
        if clip:  # corte no ponto exato exige reconverter
            plan = replace(plan, transcode_video=True, transcode_audio=True)
        transcode = plan.transcode_video or plan.transcode_audio
        self._check_space(base_dir, _part(plan.est_bytes, clip, info.duration) * (3 if transcode else 2))
        with self._workdir() as tmp:
            tracker = DownloadTracker({plan.video.format_id: plan.video.size, plan.audio.format_id: plan.audio.size})
            self._announce_clip(clip)
            self._run_ytdlp(self._source(video_args(self.tools, url, plan, tmp, clip), info, tmp), tracker)
            merged = tmp / ("media.mkv" if transcode else "media.mp4")
            self._require(merged)
            final = self._convert(merged, tmp / "final.mp4", plan, info.duration, clip) if transcode else merged
            return self._deliver(final, base_dir, "video", info, clip)

    def run_audio(self, url: str, info: VideoInfo, base_dir: Path, clip: Clip | None = None) -> Path:
        audio = best_audio(info)
        self._check_space(base_dir, _part(audio.size or 0, clip, info.duration) * 3)
        with self._workdir() as tmp:
            tracker = DownloadTracker({audio.format_id: audio.size})
            self._announce_clip(clip)
            self._run_ytdlp(self._source(audio_args(self.tools, url, audio.format_id, tmp, clip), info, tmp),
                            tracker)
            mp3 = tmp / "media.mp3"
            self._require(mp3)
            return self._deliver(mp3, base_dir, "audio", info, clip)

    def run_preview(self, info: VideoInfo, dest: Path) -> Path:
        """Baixa a cópia leve para escolher o trecho; fica em dest até o programa fechar."""
        dest.mkdir(parents=True, exist_ok=True)
        info_json = dest / "info.json"
        info_json.write_text(json.dumps(info.raw), encoding="utf-8")
        self._run_ytdlp(preview_args(self.tools, info_json, dest), DownloadTracker({}))
        found = [p for p in dest.glob("preview.*") if p.suffix in (".mkv", ".mp4", ".webm")]
        if not found:
            raise DownloadError(friendly_error(""))
        return found[0]

    def cancel(self) -> None:
        self._cancelled = True
        if self._runner:
            self._runner.cancel()

    # --- internos ----------------------------------------------------

    def _check_space(self, base_dir: Path, needed: int) -> None:
        base_dir.mkdir(parents=True, exist_ok=True)
        if self.free_space(base_dir) < needed:
            raise DownloadError(NO_SPACE)

    @contextmanager
    def _workdir(self) -> Iterator[Path]:
        path = self.tmp_root / uuid.uuid4().hex
        path.mkdir(parents=True)
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def _run(self, args: list[str], on_line: Callable[[str], None]) -> tuple[int, str]:
        if self._cancelled:
            raise Cancelled()
        tail: deque[str] = deque(maxlen=TAIL_LINES)

        def handle(line: str) -> None:
            tail.append(line)
            on_line(line)

        log.info("run: %s", args)
        self._runner = self.runner_factory()
        rc = self._runner.run(args, handle)
        self._runner = None
        if self._cancelled:
            raise Cancelled()
        output = "\n".join(tail)
        if rc != 0:
            log.error("falhou (rc=%s):\n%s", rc, output)
        return rc, output

    def _run_ytdlp(self, args: list[str], tracker: DownloadTracker) -> None:
        def on_line(line: str) -> None:
            parsed = parse_dl_line(line)
            if parsed:
                self.on_progress(tracker.update(parsed))
            elif line.startswith("[ExtractAudio]"):
                self.on_progress(Progress("mp3", None, None, None, None))

        rc, output = self._run(args, on_line)
        if rc != 0:
            raise DownloadError(friendly_error(output))

    def _source(self, args: list[str], info: VideoInfo, tmp: Path) -> list[str]:
        """Troca o link (último argumento) pela consulta já feita, se ela é recente.

        Cada consulta conta para o YouTube; repetir a da prévia dobrava os pedidos e ajudava a
        cair no bloqueio "not a bot". Os endereços dos arquivos valem algumas horas.
        """
        if not info.raw or time.time() - info.raw.get("epoch", 0) > INFO_MAX_AGE_S:
            return args
        path = tmp / "info.json"
        path.write_text(json.dumps(info.raw), encoding="utf-8")
        return args[:-1] + ["--load-info-json", str(path)]

    def _announce_clip(self, clip: Clip | None) -> None:
        """Baixando só o pedaço o yt-dlp não informa o andamento; avisa o que está acontecendo."""
        if clip:
            self.on_progress(Progress("clip", None, None, None, None))

    def _convert(self, src: Path, dst: Path, plan: VideoPlan, duration: int, clip: Clip | None = None) -> Path:
        ffmpeg = self.tools.ffmpeg_dir / "ffmpeg.exe"
        if clip:
            duration = clip[1] - clip[0]

        def on_line(line: str) -> None:
            pct = parse_ffmpeg_line(line, duration)
            if pct is not None:
                self.on_progress(Progress("convert", pct, None, None, None))

        output = ""
        encoders = [self.tools.hw_encoder] if self.tools.hw_encoder else []
        for encoder in encoders + ["x264"]:
            self.on_progress(Progress("convert", 0.0, None, None, None))
            rc, output = self._run(ffmpeg_args(ffmpeg, src, dst, plan, encoder, clip), on_line)
            if rc == 0:
                return dst
            log.warning("conversão com %s falhou, tentando a próxima", encoder)
        raise DownloadError(friendly_error(output))

    def _require(self, path: Path) -> None:
        if not path.exists():
            raise DownloadError(friendly_error(""))

    def _deliver(self, src: Path, base_dir: Path, kind, info: VideoInfo, clip: Clip | None = None) -> Path:
        with DELIVER_LOCK:  # vários downloads ao mesmo tempo: nome livre + mover, sem um sobrescrever o outro
            return self._move(src, base_dir, kind, info, clip)

    def _move(self, src: Path, base_dir: Path, kind, info: VideoInfo, clip: Clip | None) -> Path:
        dest = destination_path(base_dir, kind, info.channel, clean_title(info.title), clip_suffix(clip))
        # Entre discos diferentes o move vira cópia; copia para .part e só renomeia no fim,
        # para nunca deixar um arquivo pela metade com o nome final.
        part = dest.with_name(dest.name + ".part")
        try:
            shutil.move(str(src), str(part))
            os.replace(part, dest)
        except OSError as exc:
            part.unlink(missing_ok=True)
            log.error("falha ao mover para %s: %s", dest, exc)
            raise DownloadError(friendly_error(str(exc))) from exc
        log.info("salvo em %s", dest)
        return dest
