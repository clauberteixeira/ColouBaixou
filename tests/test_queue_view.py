from pathlib import Path

from ytdl.progress import Progress
from ytdl.queue_model import Item, Status
from ytdl.queue_view import display_title, status_text

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
