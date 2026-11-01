from pathlib import Path

from ytdl.progress import Progress
from ytdl.queue_model import Item, Status
from ytdl.queue_view import column_widths, display_title, menu_actions, row_check, row_tag, row_values, status_text

MB = 1024 * 1024


def item(status, **kw):
    return Item(id=1, video_id="abcdefghijk", kind="video", status=status, **kw)


def test_status_texts():
    assert status_text(item(Status.REVIEW)) == ("Em revisão", False)
    assert status_text(item(Status.QUEUED)) == ("Aguardando", False)
    assert status_text(item(Status.DOWNLOADING)) == ("Iniciando…", False)
    p = Progress("download", 62.0, 48 * MB, 77 * MB, 5)
    assert status_text(item(Status.DOWNLOADING, progress=p)) == ("62% · 48 MB de 77 MB · faltam ~5s", False)
    assert status_text(item(Status.DONE, path=Path("x.mp4"))) == ("✔ Concluído (clique para abrir)", False)
    assert status_text(item(Status.ERROR, error="Este vídeo é privado.")) == ("Erro: Este vídeo é privado.", True)
    assert status_text(item(Status.CANCELLED)) == ("Cancelado", False)


def test_display_title_while_loading_and_truncated():
    assert display_title(item(Status.REVIEW)) == "youtu.be/abcdefghijk (carregando…)"
    long = item(Status.QUEUED, title="x" * 100, channel="Canal")
    assert display_title(long) == "x" * 59 + "…"
    assert display_title(item(Status.QUEUED, title="Curto")) == "Curto"


def test_display_title_failed_without_details_is_not_loading():
    assert display_title(item(Status.ERROR, error="indisponível")) == "youtu.be/abcdefghijk"


def test_row_values_by_status():
    assert row_values(item(Status.REVIEW, title="T", channel="C")) == ("T", "C", "MP4 ▾", "Em revisão", "✕")
    assert row_values(item(Status.QUEUED, title="T", channel="C")) == ("T", "C", "MP4 ▾", "Aguardando", "✕")
    running = item(Status.DOWNLOADING, title="T", channel="C", progress=Progress("download", 62.0, 48 * MB, 77 * MB, 5))
    assert row_values(running) == ("T", "C", "MP4", "62% · 48 MB de 77 MB · faltam ~5s", "✕")
    assert row_values(item(Status.DONE, title="T", channel=None, path=Path("x")))[1:3] == ("", "MP4")


def test_row_check_only_in_review():
    assert row_check(item(Status.REVIEW)) == "on"
    assert row_check(item(Status.REVIEW, checked=False)) == "off"
    assert row_check(item(Status.QUEUED)) is None


def test_row_tag():
    assert row_tag(item(Status.ERROR, error="x")) == "error"
    assert row_tag(item(Status.DONE, path=Path("x"))) == "done"
    assert row_tag(item(Status.QUEUED)) == "normal"


def test_status_previously_downloaded():
    assert status_text(item(Status.DONE, path=Path("x"), previously=True)) == ("✔ Já baixado antes (clique para abrir)", False)


def test_status_shows_cancelling_instead_of_progress():
    p = Progress("download", 62.0, 48 * MB, 77 * MB, 5)
    assert status_text(item(Status.DOWNLOADING, progress=p, cancelling=True)) == ("Cancelando…", False)


def test_menu_for_waiting_items_offers_cancel_and_remove():
    for status in (Status.QUEUED, Status.REVIEW):
        assert menu_actions(item(status)) == [("Cancelar", "cancel"), ("Remover da lista", "remove")]


def test_menu_for_download_in_progress_names_the_download():
    assert menu_actions(item(Status.DOWNLOADING)) == [("Cancelar download", "cancel"), ("Remover da lista", "remove")]


def test_menu_has_no_cancel_while_already_cancelling():
    assert menu_actions(item(Status.DOWNLOADING, cancelling=True)) == [("Remover da lista", "remove")]


def test_menu_for_finished_items_only_removes():
    for status in (Status.DONE, Status.ERROR, Status.CANCELLED):
        assert menu_actions(item(status)) == [("Remover da lista", "remove")]


def test_columns_always_fill_the_list_exactly():
    # se a soma passar da largura, a última coluna (o ✕) fica cortada
    for total in (500, 588, 648, 788, 1048, 1900):
        title, status = column_widths(total, 310)
        assert title + status + 310 == total


def test_status_column_has_room_for_the_progress_at_the_default_size():
    title, status = column_widths(788, 310)
    assert status == 270 and title == 208


def test_columns_never_get_too_small_to_read():
    title, status = column_widths(300, 310)
    assert title >= 60 and status >= 60
