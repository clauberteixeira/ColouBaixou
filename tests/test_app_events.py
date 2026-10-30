import queue

from ytdl.app import drain_events
from ytdl.windowing import center_geometry


def test_handler_error_does_not_stop_other_events():
    q = queue.Queue()
    q.put(("boom", 1))
    q.put(("ok", 2))
    handled = []

    def handle(kind, payload):
        if kind == "boom":
            raise RuntimeError("falha num handler")
        handled.append((kind, payload))

    drain_events(q, handle)
    assert handled == [("ok", 2)]
    assert q.empty()


def test_window_is_centered_on_screen():
    assert center_geometry(800, 600, 1920, 1080) == (800, 600, 560, 240)


def test_window_shrinks_to_fit_small_screen():
    w, h, x, y = center_geometry(1050, 850, 1366, 768)
    assert h <= 768 * 0.92 and x >= 0 and y >= 0
    assert (x, y) == ((1366 - w) // 2, (768 - h) // 2)
