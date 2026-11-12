"""Trecho do vídeo: o que foi escolhido na linha do tempo e o nome do arquivo cortado."""

from ytdl.formats import format_duration

Clip = tuple[int, int]  # (início, fim) em segundos


def as_clip(start: int, end: int, duration: int) -> Clip | None:
    """None quando a seleção é o vídeo inteiro."""
    return None if start <= 0 and end >= duration else (start, end)


def _hms(seconds: int) -> str:
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def clip_label(clip: Clip) -> str:
    return f"{format_duration(clip[0])}–{format_duration(clip[1])}"


def clip_suffix(clip: Clip | None) -> str:
    """Final do nome do arquivo (sem ":", que o Windows não aceita)."""
    return f" (trecho {_hms(clip[0])} a {_hms(clip[1])})" if clip else ""


def split_hms(seconds: int) -> tuple[int, int, int]:
    h, rest = divmod(int(seconds), 3600)
    return (h, *divmod(rest, 60))


def join_hms(hours: str, minutes: str, seconds: str) -> int | None:
    """Campos de hora, minuto e segundo → segundos; vazio vale 0; None se tiver algo que não é número."""
    parts = [p.strip() or "0" for p in (hours, minutes, seconds)]
    if not all(p.isdigit() for p in parts):
        return None
    h, m, s = (int(p) for p in parts)
    return h * 3600 + m * 60 + s
