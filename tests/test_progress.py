import pytest

from ytdl.progress import DlLine, DownloadTracker, parse_dl_line, parse_ffmpeg_line


def test_parse_full_line():
    assert parse_dl_line("[dl]500|1000|NA|12|315") == DlLine(500, 1000, 12, "315")


def test_parse_uses_estimate_when_total_missing():
    assert parse_dl_line("[dl]500|NA|2000.5|NA|140") == DlLine(500, 2000, None, "140")


def test_unknown_total_does_not_crash():
    assert parse_dl_line("[dl]500|NA|NA|NA|140").total is None


def test_ignores_other_lines():
    assert parse_dl_line("[Merger] Merging formats into ...") is None


def test_tracker_aggregates_two_parts():
    t = DownloadTracker({"315": 1000, "140": 100})
    assert t.update(DlLine(500, 1000, 5, "315")).percent == pytest.approx(500 / 1100 * 100)
    p = t.update(DlLine(50, 100, 1, "140"))
    assert (p.downloaded, p.total) == (1050, 1100)


def test_tracker_unknown_size_gives_no_percent():
    p = DownloadTracker({"315": None}).update(DlLine(500, None, None, "315"))
    assert p.percent is None and p.downloaded == 500


def test_ffmpeg_progress():
    assert parse_ffmpeg_line("out_time_us=30000000", 60) == 50.0
    assert parse_ffmpeg_line("out_time_us=N/A", 60) is None
    assert parse_ffmpeg_line("progress=continue", 60) is None
    assert parse_ffmpeg_line("out_time_us=99000000", 60) == 100.0
    assert parse_ffmpeg_line("out_time_us=5000000", 0) is None


def test_ffmpeg_negative_start_time_is_zero():
    assert parse_ffmpeg_line("out_time_us=-33333", 60) == 0.0
