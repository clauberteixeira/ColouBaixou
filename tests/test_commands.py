from pathlib import Path

from ytdl.commands import audio_args, base_args, ffmpeg_args, info_args, video_args
from ytdl.formats import Fmt, VideoPlan
from ytdl.progress import PROGRESS_TEMPLATE
from ytdl.tools import Tools

T = Tools(Path("y.exe"), Path("ff"), Path("node.exe"))
TMP = Path("tmp")
SRC, DST = Path("in.mkv"), Path("out.mp4")


def fmt(fid, vcodec="avc1.64", acodec="none", w=1920, h=1080):
    return Fmt(fid, vcodec, acodec, "mp4", w, h, min(w, h) if w else None, 30, "SDR", 1000, 0, "https", 1)


AUDIO = fmt("140", vcodec="none", acodec="mp4a.40.2", w=None, h=None)


def plan(video=None, tv=False, ta=False, hdr=False, scale_to=None):
    return VideoPlan(video or fmt("137"), AUDIO, tv, ta, hdr, scale_to, 100)


def pair(args, flag):
    return args[args.index(flag) + 1]


def vf(args):
    return pair(args, "-vf")


def test_base_has_no_playlist_and_node():
    a = base_args(T)
    assert a[0] == "y.exe"
    assert "--no-playlist" in a and "--newline" in a
    assert pair(a, "--ffmpeg-location") == "ff"
    assert pair(a, "--progress-template") == PROGRESS_TEMPLATE
    assert pair(a, "--js-runtimes") == "node:node.exe"


def test_base_downloads_in_parallel_fragments():
    a = base_args(T)
    assert pair(a, "-N") == "8"
    assert pair(a, "--extractor-args") == "youtube:formats=dashy"


def test_base_without_node_omits_js_runtimes():
    assert "--js-runtimes" not in base_args(Tools(Path("y.exe"), Path("ff"), None))


def test_info_args_ends_with_json_url():
    assert info_args(T, "U")[-2:] == ["-J", "U"]


def test_video_args_no_transcode_merges_mp4():
    a = video_args(T, "U", plan(), TMP)
    assert pair(a, "-f") == "137+140"
    assert pair(a, "--merge-output-format") == "mp4"
    assert pair(a, "-o") == str(TMP / "media.%(ext)s")
    assert a[-1] == "U"


def test_video_args_transcode_merges_mkv():
    assert pair(video_args(T, "U", plan(tv=True), TMP), "--merge-output-format") == "mkv"
    assert pair(video_args(T, "U", plan(ta=True), TMP), "--merge-output-format") == "mkv"


def test_audio_args_mp3_320():
    a = audio_args(T, "U", "251", TMP)
    assert pair(a, "-f") == "251"
    assert pair(a, "--audio-format") == "mp3"
    assert pair(a, "--audio-quality") == "320K"
    assert "--embed-thumbnail" in a and "--embed-metadata" in a and "-x" in a
    assert pair(a, "--parse-metadata") == "%(channel)s:%(artist)s"
    assert a[-1] == "U"


def test_ffmpeg_copy_when_no_transcode():
    a = ffmpeg_args(Path("ffmpeg.exe"), SRC, DST, plan(), "nvenc")
    assert pair(a, "-c:v") == "copy" and pair(a, "-c:a") == "copy"
    assert "-vf" not in a
    assert pair(a, "-progress") == "pipe:1"


def test_ffmpeg_nvenc_sdr():
    a = ffmpeg_args(Path("ffmpeg.exe"), SRC, DST, plan(tv=True), "nvenc")
    assert pair(a, "-c:v") == "h264_nvenc"
    assert pair(a, "-preset") == "p4"
    assert vf(a) == "format=yuv420p"


def test_ffmpeg_x264_fallback():
    a = ffmpeg_args(Path("ffmpeg.exe"), SRC, DST, plan(tv=True), "x264")
    assert pair(a, "-c:v") == "libx264" and pair(a, "-crf") == "18"


def test_ffmpeg_hdr_tonemaps():
    a = ffmpeg_args(Path("ffmpeg.exe"), SRC, DST, plan(tv=True, hdr=True), "nvenc")
    assert "tonemap=tonemap=hable" in vf(a)
    assert vf(a).endswith("format=yuv420p")


def test_ffmpeg_scale_8k_to_4k():
    a = ffmpeg_args(Path("ffmpeg.exe"), SRC, DST, plan(fmt("571", "av01", w=7680, h=4320), tv=True, scale_to=2160), "nvenc")
    assert "scale=-2:2160" in vf(a)


def test_ffmpeg_scale_vertical():
    a = ffmpeg_args(Path("ffmpeg.exe"), SRC, DST, plan(fmt("v", "av01", w=4320, h=7680), tv=True, scale_to=2160), "nvenc")
    assert "scale=2160:-2" in vf(a)


def test_ffmpeg_aac_when_audio_transcode():
    a = ffmpeg_args(Path("ffmpeg.exe"), SRC, DST, plan(ta=True), "nvenc")
    assert pair(a, "-c:a") == "aac" and pair(a, "-b:a") == "192k"


def test_ffmpeg_ends_with_faststart_and_dst():
    a = ffmpeg_args(Path("ffmpeg.exe"), SRC, DST, plan(tv=True), "x264")
    assert a[-3:] == ["-movflags", "+faststart", str(DST)]


def test_ffmpeg_qsv_and_amf_encoders():
    q = ffmpeg_args(Path("ffmpeg.exe"), SRC, DST, plan(tv=True), "qsv")
    assert pair(q, "-c:v") == "h264_qsv"
    m = ffmpeg_args(Path("ffmpeg.exe"), SRC, DST, plan(tv=True), "amf")
    assert pair(m, "-c:v") == "h264_amf"
