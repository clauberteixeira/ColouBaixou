"""Reconhecimento de links de vídeo do YouTube."""

import re
from urllib.parse import parse_qs, urlparse

HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
SHORT_HOST = "youtu.be"
ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
PATH_PREFIXES = ("shorts", "embed", "live")


def _valid(candidate: str | None) -> str | None:
    return candidate if candidate and ID_RE.match(candidate) else None


def extract_video_id(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    parts = [p for p in parsed.path.split("/") if p]
    if host == SHORT_HOST:
        return _valid(parts[0]) if parts else None
    if host not in HOSTS:
        return None
    if parts == ["watch"]:
        return _valid(parse_qs(parsed.query).get("v", [None])[0])
    if len(parts) >= 2 and parts[0] in PATH_PREFIXES:
        return _valid(parts[1])
    return None


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def should_autofill(clipboard: str, current_text: str, busy: bool) -> bool:
    if busy:
        return False
    clip_id = extract_video_id(clipboard)
    return clip_id is not None and clip_id != extract_video_id(current_text)
