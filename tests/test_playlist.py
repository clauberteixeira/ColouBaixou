import json
import subprocess
from pathlib import Path

import pytest

from ytdl.commands import playlist_args
from ytdl.downloader import fetch_playlist
from ytdl.errors import DownloadError
from ytdl.playlist import parse_playlist, playlist_limit, thumb_url
from ytdl.tools import Tools

FIX = Path(__file__).parent / "fixtures"
DATA = json.loads((FIX / "playlist_mix.json").read_text("utf-8"))
TOOLS = Tools(Path("y.exe"), Path("ff"), None)


def test_parse_mix_basic():
    p = parse_playlist(DATA, 50)
    assert p.is_mix and p.truncated and p.id == "RDDB_DNxGnDzs"
    assert [e.video_id for e in p.entries][:2] == ["N2boHnDVzqY", "DB_DNxGnDzs"]
    assert p.entries[0].channel == "Diego e Victor Hugo"
    assert p.entries[0].duration == 271
    assert p.title.startswith("Mix - Humberto e Ronaldo")


def test_unavailable_entries_flagged():
    entries = parse_playlist(DATA, 50).entries
    assert entries[0].available is True
    assert entries[2].available is False
    assert entries[2].channel == "Desconhecido" and entries[2].duration == 0


def test_mix_truncated_at_50():
    many = dict(DATA, entries=[dict(DATA["entries"][0], id=f"{i:011d}") for i in range(60)])
    assert len(parse_playlist(many, 50).entries) == 50


def test_normal_playlist_truncated_flag():
    p = parse_playlist(dict(DATA, id="PL1", playlist_count=600), 500)
    assert not p.is_mix and p.truncated


def test_normal_playlist_not_truncated():
    assert parse_playlist(dict(DATA, id="PL1", playlist_count=3), 500).truncated is False


def test_entries_without_id_are_skipped():
    d = dict(DATA, entries=DATA["entries"] + [{"title": "sem id"}])
    assert len(parse_playlist(d, 50).entries) == 3


def test_limits():
    assert playlist_limit("RDxyz") == 50
    assert playlist_limit("PL1") == 500


def test_thumb_url():
    assert thumb_url("abc") == "https://i.ytimg.com/vi/abc/mqdefault.jpg"


def test_playlist_args_yes_playlist_flat():
    a = playlist_args(TOOLS, "U", 50)
    assert "--no-playlist" not in a and "--yes-playlist" in a and "--flat-playlist" in a and "-J" in a
    assert a[a.index("--playlist-end") + 1] == "50"
    assert a[-1] == "U"


def test_fetch_playlist_ok():
    run = lambda args, timeout=None: subprocess.CompletedProcess([], 0, json.dumps(DATA), "")
    assert fetch_playlist(TOOLS, "U", "RDDB_DNxGnDzs", run=run).is_mix


def test_fetch_playlist_error_is_friendly():
    run = lambda args, timeout=None: subprocess.CompletedProcess([], 1, "", "ERROR: The playlist does not exist")
    with pytest.raises(DownloadError):
        fetch_playlist(TOOLS, "U", "PL1", run=run)
