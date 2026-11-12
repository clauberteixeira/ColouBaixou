import sqlite3

from ytdl.login import firefox_status


def profile(root, name, cookies):
    folder = root / name
    folder.mkdir(parents=True)
    db = sqlite3.connect(folder / "cookies.sqlite")
    db.execute("CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT)")
    db.executemany("INSERT INTO moz_cookies VALUES (?, ?, 'x')", cookies)
    db.commit()
    db.close()
    return folder


def test_no_firefox(tmp_path):
    assert firefox_status(tmp_path / "Profiles") == "no_firefox"


def test_firefox_without_youtube_login(tmp_path):
    profile(tmp_path, "a.default", [(".youtube.com", "PREF"), (".google.com", "NID")])
    assert firefox_status(tmp_path) == "no_login"


def test_firefox_logged_in_youtube(tmp_path):
    profile(tmp_path, "a.default", [(".youtube.com", "PREF"), (".youtube.com", "__Secure-3PSID")])
    assert firefox_status(tmp_path) == "ok"


def test_uses_the_most_recent_profile_like_the_downloader(tmp_path):
    import os
    old = profile(tmp_path, "old.default", [(".youtube.com", "SAPISID")])
    new = profile(tmp_path, "new.default-release", [(".youtube.com", "PREF")])
    os.utime(old / "cookies.sqlite", (1, 1))
    assert firefox_status(tmp_path) == "no_login"
    os.utime(new / "cookies.sqlite", (1, 1))
    os.utime(old / "cookies.sqlite", None)
    assert firefox_status(tmp_path) == "ok"


def test_broken_database_is_not_a_crash(tmp_path):
    (tmp_path / "x.default").mkdir()
    (tmp_path / "x.default" / "cookies.sqlite").write_bytes(b"not a database")
    assert firefox_status(tmp_path) == "no_login"
