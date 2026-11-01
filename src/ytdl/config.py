"""Configuração do usuário (pasta, formato e janelas), gravada em config.json."""

import json
from dataclasses import dataclass, replace
from pathlib import Path

from ytdl.paths import app_data_dir


def default_base_dir() -> Path:
    return Path.home() / "Downloads" / "YouTube"


@dataclass
class Config:
    base_dir: Path
    window_size: tuple[int, int] | None = None  # no tamanho do app (antes da escala do Windows)
    maximized: bool = False
    playlist_size: tuple[int, int] | None = None
    default_kind: str = "video"  # "video" (MP4) ou "audio" (MP3)


def _default_path() -> Path:
    return app_data_dir() / "config.json"


def _window_size(value) -> tuple[int, int] | None:
    if isinstance(value, list) and len(value) == 2 and all(type(n) is int and n > 0 for n in value):
        return value[0], value[1]
    return None


def load_config(path: Path | None = None) -> Config:
    path = path or _default_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Config(base_dir=Path(data["base_dir"]), window_size=_window_size(data.get("window_size")),
                      maximized=data.get("maximized") is True,
                      playlist_size=_window_size(data.get("playlist_size")),
                      default_kind="audio" if data.get("default_kind") == "audio" else "video")
    except (OSError, ValueError, KeyError, TypeError):
        return Config(base_dir=default_base_dir())


def save_config(cfg: Config, path: Path | None = None) -> None:
    path = path or _default_path()
    data = {"base_dir": str(cfg.base_dir), "window_size": cfg.window_size, "maximized": cfg.maximized,
            "playlist_size": cfg.playlist_size, "default_kind": cfg.default_kind}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def remember_window(cfg: Config, state: str, size: tuple[int, int]) -> Config:
    """Como a janela deve abrir da próxima vez, a partir do estado do Tk ao fechar."""
    if state == "zoomed":  # guarda só o maximizado: o tamanho salvo é para quando sair dele
        return replace(cfg, maximized=True)
    if state != "normal":  # minimizada: o tamanho que o Tk informa não vale
        return cfg
    return replace(cfg, window_size=size, maximized=False)


def remember_playlist(cfg: Config, state: str, size: tuple[int, int]) -> Config:
    """A janela da playlist não maximiza: só o tamanho importa."""
    return replace(cfg, playlist_size=size) if state == "normal" else cfg
