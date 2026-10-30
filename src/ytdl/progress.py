"""Leitura das linhas de progresso do yt-dlp e do ffmpeg."""

from dataclasses import dataclass
from typing import Literal

PROGRESS_TEMPLATE = (
    "download:[dl]%(progress.downloaded_bytes)s|%(progress.total_bytes)s|"
    "%(progress.total_bytes_estimate)s|%(progress.eta)s|%(info.format_id)s"
)
PREFIX = "[dl]"


@dataclass(frozen=True)
class DlLine:
    downloaded: int
    total: int | None
    eta: int | None
    format_id: str


@dataclass(frozen=True)
class Progress:
    stage: Literal["download", "convert", "mp3"]
    percent: float | None  # 0–100
    downloaded: int | None
    total: int | None
    eta: int | None


def _num(text: str) -> int | None:
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_dl_line(line: str) -> DlLine | None:
    if not line.startswith(PREFIX):
        return None
    parts = line[len(PREFIX):].strip().split("|")
    if len(parts) != 5:
        return None
    downloaded, total, estimate, eta, format_id = parts
    return DlLine(
        downloaded=_num(downloaded) or 0,
        total=_num(total) or _num(estimate),
        eta=_num(eta),
        format_id=format_id,
    )


class DownloadTracker:
    """Soma o progresso das partes (vídeo + áudio) num único andamento."""

    def __init__(self, expected: dict[str, int | None]):
        self._sizes: dict[str, int | None] = dict(expected)
        self._done: dict[str, int] = {fid: 0 for fid in expected}
        self._current: str | None = None

    def update(self, line: DlLine) -> Progress:
        if self._current and self._current != line.format_id:
            finished = self._current
            self._done[finished] = self._sizes.get(finished) or self._done[finished]
        self._current = line.format_id
        if line.total:
            self._sizes[line.format_id] = line.total
        self._done[line.format_id] = line.downloaded

        downloaded = sum(self._done.values())
        sizes = list(self._sizes.values())
        total = sum(sizes) if sizes and all(sizes) else None
        percent = min(downloaded / total * 100, 100.0) if total else None
        return Progress("download", percent, downloaded, total, line.eta)


MB = 1024 * 1024


def _eta(seconds: int) -> str:
    return f"~{seconds}s" if seconds < 60 else f"~{round(seconds / 60)} min"


def describe(p: Progress) -> str:
    """Texto de status para a janela."""
    if p.stage == "mp3":
        return "Convertendo para MP3…"
    if p.stage == "convert":
        return f"Convertendo para formato compatível… {round(p.percent or 0)}% (pode levar alguns minutos)"
    done = round((p.downloaded or 0) / MB)
    if p.total is None:
        return f"{done} MB baixados"
    text = f"{round(p.percent or 0)}% · {done} MB de {round(p.total / MB)} MB"
    return text + (f" · faltam {_eta(p.eta)}" if p.eta else "")


def parse_ffmpeg_line(line: str, duration_s: int) -> float | None:
    key, _, value = line.strip().partition("=")
    if key != "out_time_us" or duration_s <= 0:
        return None
    micros = _num(value)
    if micros is None:
        return None
    # o ffmpeg emite tempos negativos no início
    return max(0.0, min(micros / 1_000_000 / duration_s * 100, 100.0))
