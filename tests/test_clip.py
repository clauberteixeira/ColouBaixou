from ytdl.clip import as_clip, clip_label, clip_suffix


def test_whole_selection_means_whole_video():
    assert as_clip(0, 242, 242) is None
    assert as_clip(5, 60, 242) == (5, 60)
    assert as_clip(60, 242, 242) == (60, 242)


def test_labels():
    assert clip_label((5, 60)) == "0:05–1:00"
    assert clip_suffix((5, 60)) == " (trecho 0m05s a 1m00s)"
    assert clip_suffix((3723, 3725)) == " (trecho 1h02m03s a 1h02m05s)"


def test_split_and_join_hours_minutes_seconds():
    from ytdl.clip import join_hms, split_hms
    assert split_hms(3723) == (1, 2, 3)
    assert split_hms(59) == (0, 0, 59)
    assert join_hms("1", "02", "03") == 3723
    assert join_hms("", "5", "") == 300  # campo vazio vale zero
    assert join_hms("0", "0", "90") == 90  # 90 segundos viram 1:30
    assert join_hms("0", "1a", "0") is None
    assert join_hms(" 0", "1 ", "5") == 65
