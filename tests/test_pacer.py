import pytest

from ytdl.errors import Cancelled
from ytdl.pacer import Pacer


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def make(gap=20, burst=3):
    clock = FakeClock()
    return Pacer(gap, burst, clock=clock, sleep=clock.sleep), clock


def test_first_lookups_go_right_away_then_one_every_gap():
    pacer, clock = make()
    starts = []
    for _ in range(5):
        pacer.wait()
        starts.append(clock.now - 1000)
    assert starts == [0, 0, 0, 20, 40]


def test_quiet_time_refills_the_quick_lookups():
    pacer, clock = make()
    for _ in range(3):
        pacer.wait()
    clock.now += 600  # dez minutos sem consultar
    before = clock.now
    for _ in range(3):
        pacer.wait()
    assert clock.now == before


def test_countdown_is_reported_while_waiting():
    pacer, clock = make(gap=5, burst=1)
    pacer.wait()
    seen = []
    pacer.wait(on_wait=seen.append)
    assert seen == [5, 4, 3, 2, 1]


def test_cancel_stops_the_wait():
    pacer, clock = make(gap=30, burst=1)
    pacer.wait()
    with pytest.raises(Cancelled):
        pacer.wait(cancelled=lambda: clock.now > 1010)
    assert clock.now < 1030
