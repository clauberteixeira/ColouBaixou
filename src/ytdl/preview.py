"""Prévia do trecho: comandos do ffmpeg para mostrar imagens e tocar o som da cópia leve do vídeo."""

from pathlib import Path

FRAME = (480, 270)
FPS = 15
FRAME_BYTES = FRAME[0] * FRAME[1] * 3
MAX_PREVIEW_S = 30 * 60  # vídeos maiores: sem prévia (a cópia leve ficaria pesada)
MAX_PLAY_S = 10 * 60  # cada ▶ toca no máximo isto (o som vai num arquivo temporário)
_FIT = (f"scale={FRAME[0]}:{FRAME[1]}:force_original_aspect_ratio=decrease,"
        f"pad={FRAME[0]}:{FRAME[1]}:(ow-iw)/2:(oh-ih)/2")


def frame_args(ffmpeg: Path, src: Path, t: float) -> list[str]:
    """Uma imagem no tempo t, em RGB cru do tamanho FRAME."""
    return [str(ffmpeg), "-v", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1", "-vf", _FIT,
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]


def frames_args(ffmpeg: Path, src: Path, start: float, length: float) -> list[str]:
    """Imagens seguidas (FPS por segundo) para tocar o trecho."""
    return [str(ffmpeg), "-v", "error", "-ss", f"{start:.2f}", "-t", f"{length:.2f}", "-i", str(src), "-an",
            "-vf", f"fps={FPS},{_FIT}", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]


def sound_args(ffmpeg: Path, src: Path, start: float, length: float, dst: Path) -> list[str]:
    """Som do trecho em WAV leve (o Windows toca WAV sem nada a mais)."""
    return [str(ffmpeg), "-v", "error", "-y", "-ss", f"{start:.2f}", "-t", f"{length:.2f}", "-i", str(src),
            "-vn", "-ac", "1", "-ar", "22050", str(dst)]


def play_length(position: float, end: float) -> float:
    return max(min(end - position, MAX_PLAY_S), 0.0)


def due_frame(elapsed: float) -> int:
    """Qual imagem deve estar na tela depois de `elapsed` segundos tocando."""
    return int(elapsed * FPS)
