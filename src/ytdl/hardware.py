"""Descobre qual aceleração de vídeo o computador tem (NVIDIA, Intel, AMD ou nenhuma)."""

import logging
import subprocess
from pathlib import Path

from ytdl.tools import run_quiet

log = logging.getLogger("ytdl")
ENCODER_ORDER = ("nvenc", "qsv", "amf")
PROBE_TIMEOUT = 15


def probe_args(ffmpeg: Path, encoder: str) -> list[str]:
    """Codifica alguns quadros de uma imagem sintética: só funciona se o hardware existir."""
    return [str(ffmpeg), "-hide_banner", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=640x360:r=30",
            "-frames:v", "10", "-pix_fmt", "yuv420p", "-c:v", f"h264_{encoder}", "-f", "null", "-"]


def detect_hw_encoder(ffmpeg: Path, run=run_quiet) -> str | None:
    for encoder in ENCODER_ORDER:
        try:
            if run(probe_args(ffmpeg, encoder), timeout=PROBE_TIMEOUT).returncode == 0:
                log.info("aceleração de vídeo: %s", encoder)
                return encoder
        except (subprocess.TimeoutExpired, OSError):
            pass
    log.info("aceleração de vídeo: nenhuma (conversões pelo processador)")
    return None


def prefers_fast_mode(hw_encoder: str | None) -> bool:
    """Evitar conversões por padrão? Só a NVIDIA (placa dedicada) libera o 4K como "melhor".

    Intel Quick Sync e AMD costumam ser gráficos integrados de notebook: a codificação é
    acelerada, mas ler um 4K VP9/AV1 (e o HDR) ainda pesa no processador.
    """
    return hw_encoder != "nvenc"
