import json
import subprocess
from pathlib import Path

import pytest

from ytdl.downloader import Job, cleanup_stale_temp, fetch_info
from ytdl.errors import NO_SPACE, Cancelled, DownloadError
from ytdl.formats import parse_info, plan_video
from ytdl.tools import Tools

DATA = json.loads((Path(__file__).parent / "fixtures" / "info_sample.json").read_text("utf-8"))
INFO = parse_info(DATA)
TOOLS = Tools(Path("y.exe"), Path("ff"), None, hw_encoder="nvenc")
URL = "https://www.youtube.com/watch?v=abcdefghijk"
PLENTY = lambda p: 10**13


class FakeRunner:
    """Simula yt-dlp/ffmpeg: cria o arquivo de saída na pasta temporária e emite linhas."""

    def __init__(self, scripts, log):
        self.scripts, self.log = scripts, log
        self.cancelled = False

    def run(self, args, on_line):
        self.log.append(args)
        lines, rc, create = self.scripts.pop(0)
        out_dir = Path(args[args.index("-o") + 1]).parent if "-o" in args else Path(args[-1]).parent
        if create:
            (out_dir / create).write_bytes(b"data")
        for line in lines:
            on_line(line)
        return rc

    def cancel(self):
        self.cancelled = True


def make_job(tmp_path, scripts, free_space=PLENTY):
    log, runners, events = [], [], []

    def factory():
        r = FakeRunner(scripts, log)
        runners.append(r)
        return r

    job = Job(TOOLS, tmp_path / "tmp", events.append, runner_factory=factory, free_space=free_space)
    return job, log, runners, events


def tmp_empty(tmp_path):
    root = tmp_path / "tmp"
    return not root.exists() or not any(root.iterdir())


def test_video_no_transcode_moves_to_destination(tmp_path):
    base = tmp_path / "base"
    job, log, _, events = make_job(tmp_path, [(["[dl]50|100|NA|1|137", "[dl]100|100|NA|0|137"], 0, "media.mp4")])
    result = job.run_video(URL, INFO, plan_video(INFO, 1080), base)
    assert result == base / "Vídeos" / "Canal Teste" / "Vídeo de Teste.mp4"
    assert result.exists()
    assert tmp_empty(tmp_path)
    assert len(log) == 1
    assert events and events[-1].stage == "download" and events[-1].downloaded == 100


def test_video_transcode_uses_nvenc(tmp_path):
    job, log, _, events = make_job(tmp_path, [([], 0, "media.mkv"), (["out_time_us=377000000"], 0, "final.mp4")])
    result = job.run_video(URL, INFO, plan_video(INFO), tmp_path / "base")
    assert result.exists()
    assert "h264_nvenc" in log[1]
    assert any(e.stage == "convert" and e.percent == pytest.approx(50.0) for e in events)


def test_nvenc_failure_falls_back_to_x264(tmp_path):
    job, log, _, _ = make_job(tmp_path, [([], 0, "media.mkv"), ([], 1, None), ([], 0, "final.mp4")])
    result = job.run_video(URL, INFO, plan_video(INFO), tmp_path / "base")
    assert len(log) == 3 and "libx264" in log[2]
    assert result.exists()


def test_download_error_is_friendly_and_cleans_up(tmp_path):
    base = tmp_path / "base"
    job, _, _, _ = make_job(tmp_path, [(["ERROR: Unable to download webpage: timed out"], 1, "media.mp4.part")])
    with pytest.raises(DownloadError) as exc:
        job.run_video(URL, INFO, plan_video(INFO, 1080), base)
    assert "internet" in exc.value.friendly.message
    assert tmp_empty(tmp_path)
    assert not any(p.is_file() for p in base.rglob("*"))


def test_cancel_raises_cancelled_and_cleans_up(tmp_path):
    job = None

    class CancellingRunner(FakeRunner):
        def run(self, args, on_line):
            Path(args[args.index("-o") + 1]).parent.joinpath("media.mp4.part").write_bytes(b"x")
            job.cancel()
            return 1

    runners = []

    def factory():
        r = CancellingRunner([], [])
        runners.append(r)
        return r

    job = Job(TOOLS, tmp_path / "tmp", lambda e: None, runner_factory=factory, free_space=PLENTY)
    with pytest.raises(Cancelled):
        job.run_video(URL, INFO, plan_video(INFO, 1080), tmp_path / "base")
    assert runners[0].cancelled
    assert tmp_empty(tmp_path)


def test_not_enough_space(tmp_path):
    job, log, runners, _ = make_job(tmp_path, [], free_space=lambda p: 10)
    with pytest.raises(DownloadError) as exc:
        job.run_video(URL, INFO, plan_video(INFO, 1080), tmp_path / "base")
    assert exc.value.friendly == NO_SPACE
    assert runners == []


def test_audio_mp3_destination(tmp_path):
    base = tmp_path / "base"
    job, log, _, events = make_job(tmp_path, [(["[dl]5|10|NA|1|251", "[ExtractAudio] Destination: media.mp3"], 0, "media.mp3")])
    result = job.run_audio(URL, INFO, base)
    assert result == base / "Áudios" / "Canal Teste" / "Vídeo de Teste.mp3"
    assert result.exists()
    assert "--audio-format" in log[0]
    assert events[-1].stage == "mp3"


def test_existing_file_gets_counter(tmp_path):
    base = tmp_path / "base"
    existing = base / "Áudios" / "Canal Teste" / "Vídeo de Teste.mp3"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"old")
    job, _, _, _ = make_job(tmp_path, [([], 0, "media.mp3")])
    assert job.run_audio(URL, INFO, base).name == "Vídeo de Teste (2).mp3"
    assert existing.read_bytes() == b"old"


def test_failed_move_to_other_drive_leaves_no_partial_file(tmp_path, monkeypatch):
    def broken_move(src, dst):
        Path(dst).write_bytes(b"partial")  # cópia entre discos interrompida
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("ytdl.downloader.shutil.move", broken_move)
    base = tmp_path / "base"
    job, _, _, _ = make_job(tmp_path, [([], 0, "media.mp3")])
    with pytest.raises(DownloadError) as exc:
        job.run_audio(URL, INFO, base)
    assert exc.value.friendly == NO_SPACE
    assert not any(p.is_file() for p in base.rglob("*"))
    assert tmp_empty(tmp_path)


def test_cleanup_stale_temp(tmp_path):
    (tmp_path / "abc").mkdir()
    (tmp_path / "abc" / "x.part").write_bytes(b"x")
    cleanup_stale_temp(tmp_path)
    assert not any(tmp_path.iterdir())


def completed(rc, stdout="", stderr=""):
    return subprocess.CompletedProcess([], rc, stdout, stderr)


def test_fetch_info_ok():
    info = fetch_info(TOOLS, URL, run=lambda args, timeout=None: completed(0, json.dumps(DATA)))
    assert info.title == "Vídeo de Teste"


def test_fetch_info_live_is_rejected():
    live = dict(DATA, live_status="is_live")
    with pytest.raises(DownloadError) as exc:
        fetch_info(TOOLS, URL, run=lambda args, timeout=None: completed(0, json.dumps(live)))
    assert "ao vivo" in exc.value.friendly.message


def test_fetch_info_error_is_friendly():
    with pytest.raises(DownloadError) as exc:
        fetch_info(TOOLS, URL, run=lambda args, timeout=None: completed(1, "", "ERROR: [youtube] x: Private video"))
    assert "privado" in exc.value.friendly.message


def test_transcode_uses_detected_hw_encoder_then_x264(tmp_path):
    tools = Tools(Path("y.exe"), Path("ff"), None, hw_encoder="qsv")
    log, events = [], []
    scripts = [([], 0, "media.mkv"), ([], 1, None), ([], 0, "final.mp4")]
    job = Job(tools, tmp_path / "tmp", events.append, runner_factory=lambda: FakeRunner(scripts, log),
              free_space=PLENTY)
    job.run_video(URL, INFO, plan_video(INFO), tmp_path / "base")
    assert "h264_qsv" in log[1] and "libx264" in log[2]


def test_transcode_without_hw_goes_straight_to_x264(tmp_path):
    tools = Tools(Path("y.exe"), Path("ff"), None, hw_encoder=None)
    log = []
    scripts = [([], 0, "media.mkv"), ([], 0, "final.mp4")]
    job = Job(tools, tmp_path / "tmp", lambda e: None, runner_factory=lambda: FakeRunner(scripts, log),
              free_space=PLENTY)
    job.run_video(URL, INFO, plan_video(INFO), tmp_path / "base")
    assert len(log) == 2 and "libx264" in log[1]
