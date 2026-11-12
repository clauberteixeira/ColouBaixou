import pytest

from ytdl.clip import clip_label, clip_range, clip_suffix, parse_time


@pytest.mark.parametrize("text, seconds", [
    ("0", 0), ("45", 45), ("1:30", 90), ("01:30", 90), ("1:02:03", 3723), (" 2:05 ", 125), ("90", 90),
])
def test_parse_time_accepts_seconds_minutes_and_hours(text, seconds):
    assert parse_time(text) == seconds


@pytest.mark.parametrize("text", ["", "abc", "1:60", "1:2:3:4", "-5", "1,5", ":30", "1:"])
def test_parse_time_rejects_nonsense(text):
    assert parse_time(text) is None


def test_untouched_range_means_whole_video():
    assert clip_range("0:00", "4:02", 242) is None
    assert clip_range("", "", 242) is None


def test_part_of_the_video():
    assert clip_range("0:05", "1:00", 242) == (5, 60)
    assert clip_range("1:00", "", 242) == (60, 242)  # do ponto até o fim
    assert clip_range("", "1:00", 242) == (0, 60)


def test_end_after_video_is_clamped():
    assert clip_range("1:00", "9:00", 242) == (60, 242)


def test_invalid_ranges_explain_the_problem():
    with pytest.raises(ValueError, match="1:30"):
        clip_range("abc", "1:00", 242)
    with pytest.raises(ValueError, match="antes"):
        clip_range("2:00", "1:00", 242)
    with pytest.raises(ValueError, match="antes"):
        clip_range("5:00", "", 242)


def test_labels():
    assert clip_label((5, 60)) == "0:05–1:00"
    assert clip_suffix((5, 60)) == " (trecho 0m05s a 1m00s)"
    assert clip_suffix((3723, 3725)) == " (trecho 1h02m03s a 1h02m05s)"
