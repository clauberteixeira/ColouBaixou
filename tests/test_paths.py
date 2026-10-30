from pathlib import Path

from ytdl.paths import destination_path, sanitize_component, unique_path


def test_removes_forbidden_chars():
    assert sanitize_component('a\\b/c:d*e?f"g<h>i|j') == "abcdefghij"


def test_strips_trailing_dots_and_spaces():
    assert sanitize_component("Título final. . ") == "Título final"


def test_keeps_accents_and_emoji():
    assert sanitize_component("Canção 🎵 ação") == "Canção 🎵 ação"


def test_reserved_windows_names_get_suffix():
    assert sanitize_component("CON") == "CON_"
    assert sanitize_component("nul") == "nul_"


def test_truncates_long_names():
    assert len(sanitize_component("x" * 300)) == 80


def test_empty_name_becomes_placeholder():
    assert sanitize_component("???") == "sem nome"


def test_destination_layout(tmp_path):
    p = destination_path(tmp_path, "video", "Canal: X", "Meu vídeo?")
    assert p == tmp_path / "Vídeos" / "Canal X" / "Meu vídeo.mp4"
    assert p.parent.is_dir()
    a = destination_path(tmp_path, "audio", "Canal X", "Música")
    assert a == tmp_path / "Áudios" / "Canal X" / "Música.mp3"


def test_unique_path_adds_counter(tmp_path):
    f = tmp_path / "a.mp4"
    f.write_text("x")
    assert unique_path(f) == tmp_path / "a (2).mp4"
    (tmp_path / "a (2).mp4").write_text("x")
    assert unique_path(f) == tmp_path / "a (3).mp4"


def test_destination_with_emoji_title_is_creatable(tmp_path):
    p = destination_path(tmp_path, "audio", "🎸 Rock", "🔥" * 100)
    p.write_bytes(b"ok")
    assert p.exists()
