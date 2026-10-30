"""Execução dos downloads: prévia, vídeo/áudio, conversão, cancelamento e limpeza."""

import json
import logging
import shutil
import subprocess
import threading
import uuid
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from ytdl.commands import audio_args, ffmpeg_args, info_args, video_args
from ytdl.errors import NO_SPACE, Cancelled, DownloadError, error_for_live, friendly_error
from ytdl.formats import VideoInfo, VideoPlan, available_heights, best_audio, parse_info
from ytdl.paths import destination_path
from ytdl.progress import DownloadTracker, Progress, parse_dl_line, parse_ffmpeg_line
from ytdl.tools import NO_WINDOW, Tools, run_quiet

log = logging.getLogger("ytdl")
TAIL_LINES = 50


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

    def run_video(self, url: str, info: VideoInfo, plan: VideoPlan, base_dir: Path) -> Path:
        transcode = plan.transcode_video or plan.transcode_audio
        self._check_space(base_dir, plan.est_bytes * (3 if transcode else 2))
        with self._workdir() as tmp:
            tracker = DownloadTracker({plan.video.format_id: plan.video.size, plan.audio.format_id: plan.audio.size})
            self._run_ytdlp(video_args(self.tools, url, plan, tmp), tracker)
            merged = tmp / ("media.mkv" if transcode else "media.mp4")
            self._require(merged)
            final = self._convert(merged, tmp / "final.mp4", plan, info.duration) if transcode else merged
            return self._deliver(final, base_dir, "video", info)

    def run_audio(self, url: str, info: VideoInfo, base_dir: Path) -> Path:
        audio = best_audio(info)
        self._check_space(base_dir, (audio.size or 0) * 3)
        with self._workdir() as tmp:
            tracker = DownloadTracker({audio.format_id: audio.size})
            self._run_ytdlp(audio_args(self.tools, url, audio.format_id, tmp), tracker)
            mp3 = tmp / "media.mp3"
            self._require(mp3)
            return self._deliver(mp3, base_dir, "audio", info)

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

    def _convert(self, src: Path, dst: Path, plan: VideoPlan, duration: int) -> Path:
        ffmpeg = self.tools.ffmpeg_dir / "ffmpeg.exe"

        def on_line(line: str) -> None:
            pct = parse_ffmpeg_line(line, duration)
            if pct is not None:
                self.on_progress(Progress("convert", pct, None, None, None))

        output = ""
        for encoder in ("nvenc", "x264"):
            self.on_progress(Progress("convert", 0.0, None, None, None))
            rc, output = self._run(ffmpeg_args(ffmpeg, src, dst, plan, encoder), on_line)
            if rc == 0:
                return dst
            log.warning("conversão com %s falhou, tentando a próxima", encoder)
        raise DownloadError(friendly_error(output))

    def _require(self, path: Path) -> None:
        if not path.exists():
            raise DownloadError(friendly_error(""))

    def _deliver(self, src: Path, base_dir: Path, kind, info: VideoInfo) -> Path:
        dest = destination_path(base_dir, kind, info.channel, info.title)
        shutil.move(str(src), str(dest))
        log.info("salvo em %s", dest)
        return dest
