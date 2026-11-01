import json
from pathlib import Path

import pytest

from ytdl.config import Config, load_config, remember_playlist, remember_window, save_config

DEFAULT = Path.home() / "Downloads" / "YouTube"


def test_default_base_dir_when_missing(tmp_path):
    cfg = load_config(tmp_path / "config.json")
    assert cfg.base_dir == DEFAULT


def test_roundtrip(tmp_path):
    p = tmp_path / "config.json"
    save_config(Config(base_dir=tmp_path / "Meus Vídeos"), p)
    assert load_config(p).base_dir == tmp_path / "Meus Vídeos"


def test_corrupt_file_falls_back_to_default(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{não é json", encoding="utf-8")
    assert load_config(p).base_dir == DEFAULT


def test_window_roundtrip(tmp_path):
    p = tmp_path / "config.json"
    save_config(Config(base_dir=tmp_path, window_size=(1000, 720), maximized=True), p)
    cfg = load_config(p)
    assert cfg.window_size == (1000, 720) and cfg.maximized is True


def test_config_from_older_version_has_no_window_saved(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"base_dir": str(tmp_path)}), encoding="utf-8")
    cfg = load_config(p)
    assert cfg.base_dir == tmp_path and cfg.window_size is None and cfg.maximized is False


@pytest.mark.parametrize("bad", [[0, 700], [800], ["800", "700"], [800.5, 700], "800x700", 5, [True, 700]])
def test_bad_window_size_is_ignored_and_keeps_the_folder(tmp_path, bad):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"base_dir": str(tmp_path), "window_size": bad}), encoding="utf-8")
    cfg = load_config(p)
    assert cfg.base_dir == tmp_path and cfg.window_size is None


def test_remember_window_saves_the_size_of_a_normal_window():
    cfg = Config(base_dir=Path("x"), window_size=(840, 680), maximized=True)
    assert remember_window(cfg, "normal", (1000, 720)) == Config(Path("x"), (1000, 720), False)


def test_remember_window_keeps_the_normal_size_when_maximized():
    # ao sair do maximizado, a janela volta ao tamanho que a pessoa tinha deixado
    cfg = Config(base_dir=Path("x"), window_size=(900, 700))
    assert remember_window(cfg, "zoomed", (1920, 1009)) == Config(Path("x"), (900, 700), True)


def test_remember_window_ignores_a_minimized_window():
    cfg = Config(base_dir=Path("x"), window_size=(900, 700), maximized=True)
    assert remember_window(cfg, "iconic", (160, 28)) == cfg


def test_playlist_size_roundtrip(tmp_path):
    p = tmp_path / "config.json"
    save_config(Config(base_dir=tmp_path, playlist_size=(950, 700)), p)
    assert load_config(p).playlist_size == (950, 700)


def test_bad_playlist_size_is_ignored_and_keeps_the_folder(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"base_dir": str(tmp_path), "playlist_size": "grande"}), encoding="utf-8")
    cfg = load_config(p)
    assert cfg.base_dir == tmp_path and cfg.playlist_size is None


def test_remember_playlist_saves_the_size_and_keeps_the_rest():
    cfg = Config(base_dir=Path("x"), window_size=(900, 700), maximized=True)
    assert remember_playlist(cfg, "normal", (950, 700)) == Config(Path("x"), (900, 700), True, (950, 700))


def test_remember_playlist_ignores_a_hidden_window():
    # minimizar a janela principal esconde a da playlist junto
    cfg = Config(base_dir=Path("x"), playlist_size=(950, 700))
    assert remember_playlist(cfg, "withdrawn", (1, 1)) == cfg
