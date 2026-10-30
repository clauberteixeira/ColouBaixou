import pytest

from ytdl.tools import DENO_URL, YTDLP_URL, ensure_deno, ensure_ytdlp


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


def _fake_deno_zip(url, dest):
    import zipfile
    assert url == DENO_URL
    with zipfile.ZipFile(dest, "w") as z:
        z.writestr("deno.exe", b"deno-binary")


def test_ensure_deno_downloads_and_extracts(tmp_path):
    exe = ensure_deno(tmp_path, download=_fake_deno_zip)
    assert exe == tmp_path / "deno.exe" and exe.read_bytes() == b"deno-binary"
    assert not list(tmp_path.glob("*.zip*"))


def test_ensure_deno_skips_when_present(tmp_path):
    (tmp_path / "deno.exe").write_bytes(b"x")
    ensure_deno(tmp_path, download=lambda *a: pytest.fail("não deveria baixar"))


def test_ensure_deno_failure_leaves_nothing(tmp_path):
    def boom(url, dest):
        dest.write_bytes(b"meio")
        raise OSError("rede")
    with pytest.raises(OSError):
        ensure_deno(tmp_path, download=boom)
    assert not any(tmp_path.iterdir())
