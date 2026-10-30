from pathlib import Path

from ytdl.config import Config, load_config, save_config

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
