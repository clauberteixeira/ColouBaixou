"""Pastas do aplicativo e nomes de arquivo seguros para o Windows."""

import os
import sys
from pathlib import Path
from typing import Literal

APP_NAME = "YoutubeForDownload"
FORBIDDEN = set('\\/:*?"<>|')
RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
MAX_PATH_UNITS = 240  # margem abaixo do limite de 260 do Windows

SUBFOLDER = {"video": "Vídeos", "audio": "Áudios"}
EXTENSION = {"video": ".mp4", "audio": ".mp3"}


def app_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_dir() -> Path:
    """Pasta dos arquivos que vão junto com o programa (ex.: ffmpeg)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def sanitize_component(name: str, max_len: int = 80) -> str:
    cleaned = "".join(c for c in name if c not in FORBIDDEN and ord(c) >= 32).strip()
    cleaned = cleaned[:max_len].rstrip(" .")
    if not cleaned:
        return "sem nome"
    if cleaned.split(".")[0].upper() in RESERVED:
        cleaned += "_"
    return cleaned


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def unique_path(path: Path) -> Path:
    candidate, n = path, 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        n += 1
    return candidate


def destination_path(base: Path, kind: Literal["video", "audio"], channel: str, title: str) -> Path:
    folder = base / SUBFOLDER[kind] / sanitize_component(channel)
    ext = EXTENSION[kind]
    # espaço para o nome do arquivo, reservando " (99)" para colisões
    room = MAX_PATH_UNITS - _utf16_len(str(folder)) - 1 - len(ext) - 5
    name = sanitize_component(title)
    while _utf16_len(name) > max(room, 10) and len(name) > 1:
        name = sanitize_component(name[:-1])
    folder.mkdir(parents=True, exist_ok=True)
    return unique_path(folder / f"{name}{ext}")
