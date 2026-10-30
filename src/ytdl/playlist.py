"""Leitura de playlists (`yt-dlp --flat-playlist -J`)."""

from dataclasses import dataclass

from ytdl.urls import is_mix

MIX_LIMIT = 50
PLAYLIST_LIMIT = 500
UNAVAILABLE_TITLES = {"[Private video]", "[Deleted video]"}
UNAVAILABLE_STATES = {"private", "needs_auth", "subscriber_only", "premium_only"}


@dataclass(frozen=True)
class PlaylistEntry:
    video_id: str
    title: str
    channel: str
    duration: int
    available: bool


@dataclass(frozen=True)
class Playlist:
    id: str
    title: str
    entries: tuple[PlaylistEntry, ...]
    is_mix: bool
    truncated: bool


def playlist_limit(playlist_id: str) -> int:
    return MIX_LIMIT if is_mix(playlist_id) else PLAYLIST_LIMIT


def thumb_url(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"


def _entry(raw: dict) -> PlaylistEntry:
    title = raw.get("title") or "sem título"
    return PlaylistEntry(
        video_id=raw["id"],
        title=title,
        channel=raw.get("channel") or raw.get("uploader") or "Desconhecido",
        duration=int(raw.get("duration") or 0),
        available=title not in UNAVAILABLE_TITLES and raw.get("availability") not in UNAVAILABLE_STATES,
    )


def parse_playlist(data: dict, limit: int) -> Playlist:
    raw = [e for e in (data.get("entries") or []) if e and e.get("id")]
    mix = is_mix(data.get("id") or "")
    return Playlist(
        id=data.get("id") or "",
        title=data.get("title") or "Playlist",
        entries=tuple(_entry(e) for e in raw[:limit]),
        is_mix=mix,
        truncated=mix or len(raw) > limit or (data.get("playlist_count") or 0) > limit,
    )
