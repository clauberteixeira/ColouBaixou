import pytest

from ytdl.timeline import move_handle, pick_handle, to_time, to_x

W, PAD = 420, 10  # trilho de 400 px


def test_time_and_x_round_trip():
    assert to_x(0, 200, W, PAD) == 10
    assert to_x(200, 200, W, PAD) == 410
    assert to_x(50, 200, W, PAD) == 110
    assert to_time(110, 200, W, PAD) == pytest.approx(50)


def test_time_is_clamped_to_the_video():
    assert to_time(-50, 200, W, PAD) == 0
    assert to_time(999, 200, W, PAD) == 200


def test_pick_the_nearest_handle_within_reach():
    assert pick_handle(12, 10, 110) == "start"
    assert pick_handle(105, 10, 110) == "end"
    assert pick_handle(60, 10, 110) is None


def test_handles_stacked_at_the_end_pick_start_when_dragging_left():
    # as duas alças no mesmo ponto: escolhe a que ainda pode se mexer
    assert pick_handle(410, 410, 410) == "start"
    assert pick_handle(10, 10, 10) == "end"


def test_handles_never_cross_and_keep_one_second():
    assert move_handle("start", 70, 10, 60, 200) == (59, 60)
    assert move_handle("end", 5, 10, 60, 200) == (10, 11)
    assert move_handle("end", 500, 10, 60, 200) == (10, 200)
    assert move_handle("start", -3, 10, 60, 200) == (0, 60)
    assert move_handle("start", 20.6, 10, 60, 200) == (21, 60)
