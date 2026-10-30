"""Lembra o que já foi baixado, para não baixar o mesmo vídeo duas vezes."""

import json
import logging
from pathlib import Path

from ytdl.paths import app_data_dir, planned_path

log = logging.getLogger("ytdl")


class DownloadHistory:
    """{video_id: {"video": caminho, "audio": caminho}} em history.json."""

    def __init__(self, path: Path | None = None):
        self.path = path or app_data_dir() / "history.json"
        try:
            self.data: dict[str, dict[str, str]] = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}

    def record(self, video_id: str, kind: str, file: Path) -> None:
        self.data.setdefault(video_id, {})[kind] = str(file)
        try:
            self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            log.warning("não foi possível gravar o histórico de downloads")

    def find(self, video_id: str, kind: str) -> Path | None:
        """O arquivo baixado, se ainda existir (apagou → pode baixar de novo)."""
        stored = self.data.get(video_id, {}).get(kind)
        return Path(stored) if stored and Path(stored).exists() else None


def already_downloaded(history: DownloadHistory, base: Path, video_id: str, kind: str,
                       channel: str | None, title: str | None) -> Path | None:
    """Pelo histórico ou por um arquivo com o mesmo nome na pasta (downloads antigos)."""
    found = history.find(video_id, kind)
    if found:
        return found
    if channel and title:
        expected = planned_path(base, kind, channel, title)
        if expected.exists():
            return expected
    return None
