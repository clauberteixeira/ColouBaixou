import pytest

from ytdl.urls import canonical_url, extract_video_id, should_autofill

ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize("url", [
    f"https://www.youtube.com/watch?v={ID}",
    f"https://youtube.com/watch?v={ID}&list=PL123&index=4",
    f"https://m.youtube.com/watch?v={ID}",
    f"https://music.youtube.com/watch?v={ID}&feature=share",
    f"https://youtu.be/{ID}?si=abc",
    f"https://www.youtube.com/shorts/{ID}",
    f"https://www.youtube.com/embed/{ID}",
    f"  youtube.com/watch?v={ID}  ",
])
def test_accepts_youtube_links(url):
    assert extract_video_id(url) == ID


@pytest.mark.parametrize("url", [
    "https://vimeo.com/123",
    "https://www.youtube.com/@canal",
    "https://www.youtube.com/playlist?list=PL123",
    "texto qualquer",
    "",
    "https://evil.com/watch?v=dQw4w9WgXcQ",
])
def test_rejects_other_links(url):
    assert extract_video_id(url) is None


def test_canonical_url():
    assert canonical_url(ID) == f"https://www.youtube.com/watch?v={ID}"


def test_autofill_new_link_when_idle():
    assert should_autofill(f"https://youtu.be/{ID}", "", busy=False)


def test_no_autofill_same_video_already_in_field():
    assert not should_autofill(f"https://youtu.be/{ID}", f"https://www.youtube.com/watch?v={ID}", busy=False)


def test_no_autofill_while_busy():
    assert not should_autofill(f"https://youtu.be/{ID}", "", busy=True)


def test_no_autofill_non_youtube():
    assert not should_autofill("olá", "", busy=False)
