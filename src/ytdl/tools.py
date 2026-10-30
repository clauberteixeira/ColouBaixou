"""Localiza, baixa e atualiza as ferramentas externas (yt-dlp, ffmpeg, node)."""

import os
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ytdl.paths import app_data_dir, resource_dir

YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
NO_WINDOW = subprocess.CREATE_NO_WINDOW


@dataclass(frozen=True)
class Tools:
    ytdlp: Path
    ffmpeg_dir: Path
    node: Path | None
    hw_encoder: str | None = None  # "nvenc", "qsv", "amf" ou None (só processador)


def run_quiet(args: list[str], timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(a) for a in args], capture_output=True, encoding="utf-8", errors="replace",
        creationflags=NO_WINDOW, timeout=timeout,
    )


def find_ffmpeg_dir() -> Path | None:
    bundled = resource_dir() / "ffmpeg"
    if (bundled / "ffmpeg.exe").exists():
        return bundled
    found = shutil.which("ffmpeg")
    return Path(found).parent if found else None


def find_node() -> Path | None:
    found = shutil.which("node")
    return Path(found) if found else None


def _urlretrieve(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)


def ensure_ytdlp(bin_dir: Path, download: Callable[[str, Path], None] = _urlretrieve) -> Path:
    exe = bin_dir / "yt-dlp.exe"
    if exe.exists():
        return exe
    bin_dir.mkdir(parents=True, exist_ok=True)
    part = bin_dir / "yt-dlp.exe.part"
    try:
        download(YTDLP_URL, part)
        part.replace(exe)
    finally:
        part.unlink(missing_ok=True)
    return exe


def ytdlp_version(ytdlp: Path) -> str:
    return run_quiet([ytdlp, "--version"], timeout=60).stdout.strip()


def update_ytdlp(ytdlp: Path) -> str:
    """Atualiza o yt-dlp.exe; levanta RuntimeError se não conseguir."""
    result = run_quiet([ytdlp, "-U"], timeout=300)
    if result.returncode != 0:
        raise RuntimeError((result.stdout + result.stderr).strip())
    return ytdlp_version(ytdlp)


def load_tools() -> Tools:
    ytdlp = ensure_ytdlp(app_data_dir() / "bin")
    ffmpeg_dir = find_ffmpeg_dir()
    if ffmpeg_dir is None:
        raise RuntimeError("FFmpeg não encontrado.")
    from ytdl.hardware import detect_hw_encoder  # evita import circular (hardware usa run_quiet)

    # YTDL_NO_NODE / YTDL_NO_HW simulam um computador sem Node.js / sem aceleração (testes)
    node = None if os.environ.get("YTDL_NO_NODE") else find_node()
    hw = None if os.environ.get("YTDL_NO_HW") else detect_hw_encoder(ffmpeg_dir / "ffmpeg.exe")
    return Tools(ytdlp=ytdlp, ffmpeg_dir=ffmpeg_dir, node=node, hw_encoder=hw)
