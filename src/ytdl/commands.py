"""Montagem das linhas de comando do yt-dlp e do ffmpeg (sem efeitos colaterais)."""

from pathlib import Path
from typing import Literal

from ytdl.formats import VideoPlan
from ytdl.progress import PROGRESS_TEMPLATE
from ytdl.tools import Tools

OUTPUT_NAME = "media.%(ext)s"
TONEMAP = (
    "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
    "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv"
)
ENCODERS = {
    # p4: medido ~1,7x mais rápido que p5 no 4K60, mesmo tamanho, SSIM 0,996
    "nvenc": ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "19", "-b:v", "0", "-profile:v", "high"],
    "qsv": ["-c:v", "h264_qsv", "-preset", "medium", "-global_quality", "20", "-profile:v", "high"],
    "amf": ["-c:v", "h264_amf", "-quality", "quality", "-rc", "cqp", "-qp_i", "20", "-qp_p", "20",
            "-profile:v", "high"],
    "x264": ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high"],
}


def base_args(t: Tools) -> list[str]:
    args = [
        str(t.ytdlp), "--no-playlist", "--encoding", "utf-8",
        "--ffmpeg-location", str(t.ffmpeg_dir),
        "--newline", "--progress-template", PROGRESS_TEMPLATE,
        # baixa em 8 partes paralelas (medido: ~2,2x mais rápido, mesmo arquivo)
        "-N", "8", "--extractor-args", "youtube:formats=dashy",
    ]
    if t.node:
        args += ["--js-runtimes", f"node:{t.node}"]
    return args


def playlist_args(t: Tools, url: str, limit: int) -> list[str]:
    # sem base_args: ele tem --no-playlist
    args = [str(t.ytdlp), "--yes-playlist", "--flat-playlist", "-J",
            "--playlist-end", str(limit), "--encoding", "utf-8"]
    if t.node:
        args += ["--js-runtimes", f"node:{t.node}"]
    return args + [url]


def info_args(t: Tools, url: str) -> list[str]:
    return base_args(t) + ["-J", url]


def video_args(t: Tools, url: str, plan: VideoPlan, tmp: Path) -> list[str]:
    container = "mkv" if plan.transcode_video or plan.transcode_audio else "mp4"
    return base_args(t) + [
        "-f", f"{plan.video.format_id}+{plan.audio.format_id}",
        "--merge-output-format", container,
        "-o", str(tmp / OUTPUT_NAME), url,
    ]


def audio_args(t: Tools, url: str, audio_format_id: str, tmp: Path) -> list[str]:
    return base_args(t) + [
        "-f", audio_format_id, "-x", "--audio-format", "mp3", "--audio-quality", "320K",
        "--embed-thumbnail", "--embed-metadata", "--parse-metadata", "%(channel)s:%(artist)s",
        "-o", str(tmp / OUTPUT_NAME), url,
    ]


def _filters(plan: VideoPlan) -> str:
    chain = []
    if plan.hdr:
        chain.append(TONEMAP)
    if plan.scale_to:
        v = plan.video
        horizontal = (v.width or 0) >= (v.height or 0)
        chain.append(f"scale=-2:{plan.scale_to}" if horizontal else f"scale={plan.scale_to}:-2")
    chain.append("format=yuv420p")
    return ",".join(chain)


def ffmpeg_args(ffmpeg: Path, src: Path, dst: Path, plan: VideoPlan,
                encoder: Literal["nvenc", "qsv", "amf", "x264"]) -> list[str]:
    args = [str(ffmpeg), "-y", "-hide_banner", "-nostats", "-progress", "pipe:1",
            "-i", str(src), "-map", "0:v:0", "-map", "0:a:0"]
    if plan.transcode_video:
        args += ["-vf", _filters(plan)] + ENCODERS[encoder]
    else:
        args += ["-c:v", "copy"]
    args += ["-c:a", "aac", "-b:a", "192k"] if plan.transcode_audio else ["-c:a", "copy"]
    return args + ["-movflags", "+faststart", str(dst)]
