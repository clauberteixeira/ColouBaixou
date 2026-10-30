"""Reconhecimento de links de vídeo do YouTube."""

import re
from urllib.parse import parse_qs, urlparse

HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
SHORT_HOST = "youtu.be"
ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
PATH_PREFIXES = ("shorts", "embed", "live")


def _valid(candidate: str | None) -> str | None:
    return candidate if candidate and ID_RE.match(candidate) else None


def _parse(text: str):
    """Devolve o link analisado e o host, ou None se não for do YouTube."""
    text = text.strip()
    if not text:
        return None
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if host != SHORT_HOST and host not in HOSTS:
        return None
    return parsed, host


def extract_video_id(text: str) -> str | None:
    result = _parse(text)
    if result is None:
        return None
    parsed, host = result
    parts = [p for p in parsed.path.split("/") if p]
    if host == SHORT_HOST:
        return _valid(parts[0]) if parts else None
    if parts == ["watch"]:
        return _valid(parse_qs(parsed.query).get("v", [None])[0])
    if len(parts) >= 2 and parts[0] in PATH_PREFIXES:
        return _valid(parts[1])
    return None


def extract_video_ids(text: str) -> list[str]:
    """Todos os vídeos de um texto colado, na ordem e sem repetir."""
    ids: list[str] = []
    for piece in text.split():
        video_id = extract_video_id(piece)
        if video_id and video_id not in ids:
            ids.append(video_id)
    return ids


def extract_playlist_id(text: str) -> str | None:
    result = _parse(text)
    if result is None:
        return None
    parsed, _ = result
    playlist_id = parse_qs(parsed.query).get("list", [None])[0]
    return playlist_id or None


def is_mix(playlist_id: str) -> bool:
    """Mix do YouTube: playlist gerada automaticamente e sem fim."""
    return playlist_id.startswith("RD")


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def should_autofill(clipboard: str, current_text: str, busy: bool) -> bool:
    if busy:
        return False
    clip_id = extract_video_id(clipboard)
    return clip_id is not None and clip_id != extract_video_id(current_text)
