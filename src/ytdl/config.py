"""Configuração do usuário (pasta principal), gravada em config.json."""

import json
from dataclasses import dataclass
from pathlib import Path

from ytdl.paths import app_data_dir


def default_base_dir() -> Path:
    return Path.home() / "Downloads" / "YouTube"


@dataclass
class Config:
    base_dir: Path


def _default_path() -> Path:
    return app_data_dir() / "config.json"


def load_config(path: Path | None = None) -> Config:
    path = path or _default_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Config(base_dir=Path(data["base_dir"]))
    except (OSError, ValueError, KeyError, TypeError):
        return Config(base_dir=default_base_dir())


def save_config(cfg: Config, path: Path | None = None) -> None:
    path = path or _default_path()
    path.write_text(json.dumps({"base_dir": str(cfg.base_dir)}, ensure_ascii=False), encoding="utf-8")
