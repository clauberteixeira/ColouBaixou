from pathlib import Path

from ytdl.queue_model import QueueModel, Status

A, B, C, D = "aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc", "ddddddddddd"


def test_add_and_duplicate_same_kind_rejected():
    m = QueueModel()
    assert m.add(A, "video", Status.QUEUED) is not None
    assert m.add(A, "video", Status.REVIEW) is None
    assert m.add(A, "audio", Status.QUEUED) is not None
    assert len(m.items) == 2


def test_duplicate_allowed_after_finished():
    m = QueueModel()
    first = m.add(A, "video", Status.QUEUED)
    m.start(first.id)
    m.finish(first.id, Path("x.mp4"))
    assert m.add(A, "video", Status.QUEUED) is not None


def test_review_items_never_picked_even_while_running():
    m = QueueModel()
    q1 = m.add(A, "video", Status.QUEUED)
    m.start(q1.id)
    m.add(B, "video", Status.REVIEW)
    m.add(C, "audio", Status.REVIEW)
    assert m.next_item() is None


def test_release_checked_only_marked():
    m = QueueModel()
    items = [m.add(v, "video", Status.REVIEW) for v in (A, B, C)]
    assert m.set_checked(items[1].id, False)
    assert m.release_checked() == 2
    assert [i.status for i in items] == [Status.QUEUED, Status.REVIEW, Status.QUEUED]


def test_next_item_follows_release_order():
    m = QueueModel()
    x = m.add(A, "video", Status.REVIEW)
    y = m.add(B, "video", Status.REVIEW)
    z = m.add(C, "video", Status.QUEUED)
    m.release_checked()
    order = []
    while (item := m.next_item()) is not None:
        order.append(item.id)
        m.start(item.id)
        m.finish(item.id, Path("f"))
    assert order == [z.id, x.id, y.id]


def test_error_does_not_stop_queue():
    m = QueueModel()
    q1 = m.add(A, "video", Status.QUEUED)
    q2 = m.add(B, "video", Status.QUEUED)
    m.start(q1.id)
    m.fail(q1.id, "Este vídeo está indisponível ou foi removido.")
    assert q1.status == Status.ERROR and q1.error.startswith("Este vídeo")
    assert m.next_item() is q2


def test_cancel_all_keeps_review():
    m = QueueModel()
    d = m.add(A, "video", Status.QUEUED)
    e = m.add(B, "video", Status.QUEUED)
    f = m.add(C, "video", Status.REVIEW)
    m.start(d.id)
    assert m.cancel_all() == [d]
    assert e.status == Status.CANCELLED
    assert f.status == Status.REVIEW
    assert m.next_item() is None


def test_cancel_all_with_nothing_running():
    m = QueueModel()
    e = m.add(B, "video", Status.QUEUED)
    assert m.cancel_all() == []
    assert e.status == Status.CANCELLED


def test_remove_downloading_returns_it_and_next_continues():
    m = QueueModel()
    d = m.add(A, "video", Status.QUEUED)
    nxt = m.add(B, "video", Status.QUEUED)
    m.start(d.id)
    removed = m.remove(d.id)
    assert removed is d and removed.status == Status.DOWNLOADING
    assert m.get(d.id) is None and d not in m.items
    assert m.downloading() == []
    assert m.next_item() is nxt


def test_set_kind_and_checked_locked_after_start():
    m = QueueModel()
    r = m.add(A, "video", Status.REVIEW)
    q = m.add(B, "video", Status.QUEUED)
    assert m.set_kind(q.id, "audio") and q.kind == "audio"
    assert not m.set_checked(q.id, False)  # caixinha só existe em revisão
    m.release_checked()
    m.start(r.id)
    assert not m.set_kind(r.id, "audio")
    assert not m.set_checked(r.id, False)


def test_set_kind_rejects_duplicate():
    m = QueueModel()
    m.add(A, "video", Status.QUEUED)
    audio = m.add(A, "audio", Status.QUEUED)
    assert not m.set_kind(audio.id, "video")
    assert audio.kind == "audio"


def test_clear_finished():
    m = QueueModel()
    done, err, canc = (m.add(v, "video", Status.QUEUED) for v in (A, B, C))
    keep_q = m.add(D, "video", Status.QUEUED)
    keep_r = m.add(D, "audio", Status.REVIEW)
    m.start(done.id)
    m.finish(done.id, Path("f"))
    m.fail(err.id, "erro")
    m.mark_cancelled(canc.id)
    assert m.clear_finished() == 3
    assert m.items == [keep_q, keep_r]


def test_review_checked_count():
    m = QueueModel()
    a = m.add(A, "video", Status.REVIEW)
    m.add(B, "video", Status.REVIEW)
    m.add(C, "video", Status.QUEUED)
    m.set_checked(a.id, False)
    assert m.review_checked_count() == 1


def test_add_keeps_extra_fields():
    m = QueueModel()
    item = m.add(A, "audio", Status.QUEUED, title="Música", channel="Canal", duration=200, res=None)
    assert (item.title, item.channel, item.duration, item.checked) == ("Música", "Canal", 200, True)


def test_requeue_puts_item_back_first():
    m = QueueModel()
    a = m.add(A, "video", Status.QUEUED)
    b = m.add(B, "video", Status.QUEUED)
    m.start(a.id)
    m.fail(a.id, "bloqueado")
    m.requeue(a.id)
    assert a.status == Status.QUEUED and a.error is None
    assert m.next_item() is a
    assert b.status == Status.QUEUED


def test_mark_previously_downloaded():
    m = QueueModel()
    r = m.add(A, "video", Status.REVIEW)
    m.mark_previously_downloaded(r.id, Path("x.mp4"))
    assert r.status == Status.DONE and r.previously and r.path == Path("x.mp4")
    assert m.review_checked_count() == 0


def test_several_downloading_at_once():
    m = QueueModel()
    a, b, c = (m.add(v, "audio", Status.QUEUED) for v in (A, B, C))
    m.start(m.next_item().id)
    m.start(m.next_item().id)
    assert m.downloading() == [a, b]
    assert m.next_item() is c
    assert m.cancel_all() == [a, b] and c.status == Status.CANCELLED


def test_cancel_waiting_item_lets_the_queue_move_on():
    m = QueueModel()
    first = m.add(A, "video", Status.QUEUED)
    second = m.add(B, "video", Status.QUEUED)
    assert m.cancel(first.id) is False
    assert first.status == Status.CANCELLED
    assert m.next_item() is second


def test_cancel_item_in_review():
    m = QueueModel()
    item = m.add(A, "video", Status.REVIEW)
    assert m.cancel(item.id) is False
    assert item.status == Status.CANCELLED


def test_cancel_download_waits_for_the_job_to_stop():
    m = QueueModel()
    item = m.add(A, "video", Status.QUEUED)
    m.start(item.id)
    assert m.cancel(item.id) is True
    assert item.status == Status.DOWNLOADING and item.cancelling is True
    m.mark_cancelled(item.id)
    assert item.status == Status.CANCELLED


def test_cancel_finished_item_changes_nothing():
    m = QueueModel()
    item = m.add(A, "video", Status.QUEUED)
    m.start(item.id)
    m.finish(item.id, Path("x.mp4"))
    assert m.cancel(item.id) is False
    assert item.status == Status.DONE


def test_cancel_unknown_item_changes_nothing():
    assert QueueModel().cancel(99) is False


def test_requeue_forgets_a_pending_cancel():
    m = QueueModel()
    item = m.add(A, "video", Status.QUEUED)
    m.start(item.id)
    m.cancel(item.id)
    m.requeue(item.id)
    assert item.status == Status.QUEUED and item.cancelling is False
