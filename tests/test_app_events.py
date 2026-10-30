import queue

from ytdl.app import drain_events


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
