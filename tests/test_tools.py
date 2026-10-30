import pytest

from ytdl.tools import YTDLP_URL, ensure_ytdlp


def test_ensure_ytdlp_downloads_when_missing(tmp_path):
    calls = []

    def fake(url, dest):
        calls.append(url)
        dest.write_bytes(b"exe")

    p = ensure_ytdlp(tmp_path, download=fake)
    assert p == tmp_path / "yt-dlp.exe"
    assert p.read_bytes() == b"exe"
    assert calls == [YTDLP_URL]


def test_ensure_ytdlp_skips_when_present(tmp_path):
    (tmp_path / "yt-dlp.exe").write_bytes(b"x")
    ensure_ytdlp(tmp_path, download=lambda *a: pytest.fail("não deveria baixar"))


def test_failed_download_leaves_no_exe(tmp_path):
    def boom(url, dest):
        dest.write_bytes(b"meio")
        raise OSError("rede")

    with pytest.raises(OSError):
        ensure_ytdlp(tmp_path, download=boom)
    assert not (tmp_path / "yt-dlp.exe").exists()
    assert not (tmp_path / "yt-dlp.exe.part").exists()
