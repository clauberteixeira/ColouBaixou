import subprocess
from pathlib import Path

from ytdl.hardware import ENCODER_ORDER, detect_hw_encoder, probe_args

FF = Path("ffmpeg.exe")


def fake_run(working: set[str], calls: list):
    def run(args, timeout=None):
        enc = args[args.index("-c:v") + 1]
        calls.append(enc)
        return subprocess.CompletedProcess(args, 0 if enc in working else 1, "", "")
    return run


def test_order():
    assert ENCODER_ORDER == ("nvenc", "qsv", "amf")


def test_probe_args_encodes_synthetic_frames():
    a = probe_args(FF, "qsv")
    assert a[0] == "ffmpeg.exe" and "lavfi" in a
    assert a[a.index("-c:v") + 1] == "h264_qsv"
    assert a[-3:] == ["-f", "null", "-"]


def test_first_working_encoder_wins():
    calls = []
    assert detect_hw_encoder(FF, run=fake_run({"h264_qsv", "h264_amf"}, calls)) == "qsv"
    assert calls == ["h264_nvenc", "h264_qsv"]


def test_none_when_nothing_works():
    assert detect_hw_encoder(FF, run=fake_run(set(), [])) is None


def test_timeout_counts_as_failure():
    def run(args, timeout=None):
        raise subprocess.TimeoutExpired(args, timeout)
    assert detect_hw_encoder(FF, run=run) is None
