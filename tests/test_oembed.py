import io
import json
import urllib.error

import pytest

from ytdl.downloader import fetch_oembed
from ytdl.errors import DownloadError


def opener_returning(payload):
    def opener(url, timeout=None):
        assert "oembed" in url and "abcdefghijk" in url
        return io.BytesIO(json.dumps(payload).encode())
    return opener


def opener_raising(exc):
    def opener(url, timeout=None):
        raise exc
    return opener


def test_oembed_title_and_channel():
    got = fetch_oembed("abcdefghijk", opener_returning({"title": "Música", "author_name": "Canal"}))
    assert got == ("Música", "Canal")


def test_oembed_not_found_is_unavailable():
    err = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
    with pytest.raises(DownloadError) as exc:
        fetch_oembed("abcdefghijk", opener_raising(err))
    assert "indisponível" in exc.value.friendly.message


def test_oembed_unauthorized_falls_back():
    err = urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)
    assert fetch_oembed("abcdefghijk", opener_raising(err)) is None


def test_oembed_network_error_falls_back():
    assert fetch_oembed("abcdefghijk", opener_raising(urllib.error.URLError("offline"))) is None
