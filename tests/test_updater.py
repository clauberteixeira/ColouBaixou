import io
import json
import urllib.error

import pytest

from ytdl.updater import Release, check_latest, download_installer, install_args, parse_version

ASSET = "https://github.com/clauberteixeira/ColouBaixou/releases/download/v1.1.0/ColouBaixou-Setup-1.1.0.exe"


def api_payload(tag="v1.1.0", assets=None):
    if assets is None:
        assets = [{"name": "ColouBaixou-Setup-1.1.0.exe", "browser_download_url": ASSET, "size": 12}]
    return {"tag_name": tag, "html_url": f"https://github.com/clauberteixeira/ColouBaixou/releases/tag/{tag}",
            "assets": assets}


def opener_json(payload):
    def opener(url, timeout=None):
        assert "api.github.com/repos/clauberteixeira/ColouBaixou/releases/latest" in url
        return io.BytesIO(json.dumps(payload).encode())
    return opener


def test_parse_version():
    assert parse_version("v1.2.10") == (1, 2, 10)
    assert parse_version("1.0.0") == (1, 0, 0)
    assert parse_version("nightly") is None


def test_newer_release_found():
    r = check_latest("1.0.0", opener=opener_json(api_payload()))
    assert r == Release("1.1.0", "https://github.com/clauberteixeira/ColouBaixou/releases/tag/v1.1.0", ASSET, 12)


@pytest.mark.parametrize("tag", ["v1.0.0", "v0.9.9"])
def test_same_or_older_is_none(tag):
    assert check_latest("1.0.0", opener=opener_json(api_payload(tag))) is None


def test_release_without_installer_is_none():
    assert check_latest("1.0.0", opener=opener_json(api_payload(assets=[{"name": "notes.txt"}]))) is None


def test_network_or_api_error_is_none():
    def offline(url, timeout=None):
        raise urllib.error.URLError("offline")

    def not_found(url, timeout=None):
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    assert check_latest("1.0.0", opener=offline) is None
    assert check_latest("1.0.0", opener=not_found) is None
    assert check_latest("1.0.0", opener=lambda u, timeout=None: io.BytesIO(b"<html>")) is None


def test_download_installer(tmp_path):
    progress = []
    release = Release("1.1.0", "u", ASSET, 12)
    path = download_installer(release, tmp_path, opener=lambda u, timeout=None: io.BytesIO(b"x" * 12),
                              on_progress=progress.append)
    assert path == tmp_path / "ColouBaixou-Setup-1.1.0.exe"
    assert path.read_bytes() == b"x" * 12
    assert progress[-1] == 100.0
    assert not list(tmp_path.glob("*.part"))


def test_incomplete_download_leaves_nothing(tmp_path):
    release = Release("1.1.0", "u", ASSET, 12)
    with pytest.raises(OSError):
        download_installer(release, tmp_path, opener=lambda u, timeout=None: io.BytesIO(b"x" * 5))
    assert not any(tmp_path.iterdir())


def test_install_args_silent_and_closes_app(tmp_path):
    args = install_args(tmp_path / "setup.exe")
    assert args[0] == str(tmp_path / "setup.exe")
    assert {"/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"} <= set(args)
