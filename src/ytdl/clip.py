"""Trecho do vídeo: ler os tempos digitados e dar nome ao arquivo cortado."""

from ytdl.formats import format_duration

Clip = tuple[int, int]  # (início, fim) em segundos

BAD_TIME = "Tempo inválido. Use minutos:segundos, por exemplo 1:30."
BAD_ORDER = "O início do trecho precisa ser antes do fim."


def parse_time(text: str) -> int | None:
    """"90", "1:30" ou "1:02:03" → segundos; None se não for um tempo."""
    parts = text.strip().split(":")
    if len(parts) > 3 or not all(p.isdigit() for p in parts):
        return None
    nums = [int(p) for p in parts]
    if any(n >= 60 for n in nums[1:]):
        return None
    total = 0
    for n in nums:
        total = total * 60 + n
    return total


def clip_range(start: str, end: str, duration: int) -> Clip | None:
    """Trecho escolhido; None = vídeo inteiro. ValueError com a explicação se não der."""
    s = parse_time(start) if start.strip() else 0
    e = parse_time(end) if end.strip() else duration
    if s is None or e is None:
        raise ValueError(BAD_TIME)
    if duration:
        e = min(e, duration)
    if s >= e:
        raise ValueError(BAD_ORDER)
    if s == 0 and e == duration:
        return None
    return s, e


def _hms(seconds: int) -> str:
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def clip_label(clip: Clip) -> str:
    return f"{format_duration(clip[0])}–{format_duration(clip[1])}"


def clip_suffix(clip: Clip | None) -> str:
    """Final do nome do arquivo (sem ":", que o Windows não aceita)."""
    return f" (trecho {_hms(clip[0])} a {_hms(clip[1])})" if clip else ""
