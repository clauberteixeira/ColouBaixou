"""Leitura do `yt-dlp -J` e escolha do que baixar."""

from dataclasses import dataclass

CAP = 2160


@dataclass(frozen=True)
class Fmt:
    format_id: str
    vcodec: str
    acodec: str
    ext: str
    width: int | None
    height: int | None
    res: int | None  # min(width, height); None em áudio
    fps: float
    dynamic_range: str
    tbr: float
    abr: float
    protocol: str
    size: int | None
    lang_pref: int = 0  # yt-dlp: 10 = áudio original, -1 = dublado


@dataclass(frozen=True)
class VideoInfo:
    id: str
    title: str
    channel: str
    duration: int
    thumbnail_url: str | None
    live_status: str | None
    video_formats: tuple[Fmt, ...]
    audio_formats: tuple[Fmt, ...]


@dataclass(frozen=True)
class VideoPlan:
    video: Fmt
    audio: Fmt
    transcode_video: bool
    transcode_audio: bool
    hdr: bool
    scale_to: int | None
    est_bytes: int


def _fmt(d: dict) -> Fmt:
    w, h = d.get("width"), d.get("height")
    return Fmt(
        format_id=str(d.get("format_id")),
        vcodec=d.get("vcodec") or "none",
        acodec=d.get("acodec") or "none",
        ext=d.get("ext") or "",
        width=w,
        height=h,
        res=min(w, h) if w and h else None,
        fps=float(d.get("fps") or 0),
        dynamic_range=d.get("dynamic_range") or "SDR",
        tbr=float(d.get("tbr") or 0),
        abr=float(d.get("abr") or 0),
        protocol=d.get("protocol") or "",
        size=d.get("filesize") or d.get("filesize_approx"),
        lang_pref=int(d.get("language_preference") or 0),
    )


def parse_info(data: dict) -> VideoInfo:
    video, audio = [], []
    for raw in data.get("formats") or []:
        if raw.get("has_drm") or raw.get("ext") == "mhtml":
            continue
        f = _fmt(raw)
        if f.vcodec != "none" and f.acodec == "none" and f.res:
            video.append(f)
        elif f.vcodec == "none" and f.acodec != "none":
            audio.append(f)
    return VideoInfo(
        id=data.get("id") or "",
        title=data.get("title") or "sem título",
        channel=data.get("channel") or data.get("uploader") or "Desconhecido",
        duration=int(data.get("duration") or 0),
        thumbnail_url=data.get("thumbnail"),
        live_status=data.get("live_status"),
        video_formats=tuple(video),
        audio_formats=tuple(audio),
    )


def available_heights(info: VideoInfo) -> list[int]:
    all_res = {f.res for f in info.video_formats}
    capped = sorted((r for r in all_res if r <= CAP), reverse=True)
    if not capped and all_res:
        return [CAP]
    return capped


def _video_key(f: Fmt):
    return (f.fps, f.dynamic_range == "SDR", f.vcodec.startswith("avc1"), f.protocol == "https", f.tbr)


def _fast_key(f: Fmt):
    """Computador sem aceleração: o que não precisa de conversão vem antes de fps."""
    return (f.vcodec.startswith("avc1"), f.dynamic_range == "SDR", f.fps, f.protocol == "https", f.tbr)


def _no_conversion(f: Fmt) -> bool:
    return f.vcodec.startswith("avc1") and f.dynamic_range == "SDR"


def best_fast_height(info: VideoInfo) -> int | None:
    """Maior resolução (até 4K) que existe em H.264 SDR, ou seja, sem conversão."""
    fast = [f.res for f in info.video_formats if _no_conversion(f) and f.res <= CAP]
    return max(fast) if fast else None


def _estimate(f: Fmt, duration: int) -> float:
    return f.size if f.size is not None else (f.tbr or f.abr) * 125 * duration


def plan_video(info: VideoInfo, res: int | None = None, fast: bool = False) -> VideoPlan:
    """fast=True: computador sem aceleração de vídeo (evita conversões lentas)."""
    target = res or (fast and best_fast_height(info)) or available_heights(info)[0]
    candidates = [f for f in info.video_formats if f.res == target]
    scale_to = None
    if not candidates:
        above = [f for f in info.video_formats if f.res > CAP]
        lowest = min(f.res for f in above)
        candidates = [f for f in above if f.res == lowest]
        scale_to = CAP
    video = max(candidates, key=_fast_key if fast else _video_key)
    hdr = video.dynamic_range != "SDR"

    pool = _audio_pool(info)
    m4a = [f for f in pool if f.acodec.startswith("mp4a")]
    audio = max(m4a or pool, key=_audio_key)

    return VideoPlan(
        video=video,
        audio=audio,
        transcode_video=not video.vcodec.startswith("avc1") or hdr or scale_to is not None,
        transcode_audio=not m4a,
        hdr=hdr,
        scale_to=scale_to,
        est_bytes=int(_estimate(video, info.duration) + _estimate(audio, info.duration)),
    )


def _audio_pool(info: VideoInfo) -> tuple[Fmt, ...]:
    """Evita o áudio "-drc" (faixa dinâmica comprimida) quando há a versão normal."""
    normal = tuple(f for f in info.audio_formats if not f.format_id.endswith("-drc"))
    return normal or info.audio_formats


def _audio_key(f: Fmt):
    """Idioma original antes de bitrate: o -f explícito ignora a preferência do yt-dlp."""
    return (f.lang_pref, f.abr)


def best_audio(info: VideoInfo) -> Fmt:
    return max(_audio_pool(info), key=_audio_key)


def quality_label(res: int) -> str:
    return {2160: "4K", 1440: "1440p (2K)"}.get(res, f"{res}p")


BEST = "Melhor disponível"
SLOW = "lenta neste PC"


def quality_options(info: VideoInfo, fast: bool) -> dict[str, int | None]:
    """Rótulos do seletor de qualidade → resolução (None = melhor para este computador)."""
    heights = available_heights(info)
    best = (fast and best_fast_height(info)) or heights[0]
    options: dict[str, int | None] = {f"{BEST} ({quality_label(best)})": None}
    for h in heights:
        if h != best:
            slow = fast and h > best
            options[f"{quality_label(h)} ({SLOW})" if slow else quality_label(h)] = h
    return options


def format_duration(seconds: int) -> str:
    h, rest = divmod(int(seconds), 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
