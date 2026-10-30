from ytdl.playlist import PlaylistEntry
from ytdl.playlist_window import entry_state, selection_summary

OK = PlaylistEntry("aaaaaaaaaaa", "Música", "Canal", 200, True)
PRIVATE = PlaylistEntry("bbbbbbbbbbb", "[Private video]", "Desconhecido", 0, False)


def test_entry_state():
    assert entry_state(OK, checked=True, downloaded=False) == "on"
    assert entry_state(OK, checked=False, downloaded=False) == "off"
    assert entry_state(OK, checked=True, downloaded=True) == "disabled"
    assert entry_state(PRIVATE, checked=False, downloaded=False) == "disabled"


def test_selection_summary():
    assert selection_summary(50, 0, 0) == "50 vídeos · nenhum selecionado"
    assert selection_summary(50, 1, 0) == "50 vídeos · 1 selecionado"
    assert selection_summary(50, 3, 2) == "50 vídeos · 3 selecionados · 2 já baixados"
    assert selection_summary(1, 0, 1) == "1 vídeo · nenhum selecionado · 1 já baixado"
