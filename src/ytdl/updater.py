"""Atualização do próprio ColouBaixô pelas versões publicadas no GitHub."""

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ytdl.about import REPO

log = logging.getLogger("ytdl")
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET_RE = re.compile(r"^ColouBaixou-Setup-.*\.exe$", re.IGNORECASE)
VERSION_RE = re.compile(r"^v?(\d+(?:\.\d+)*)$")
CHUNK = 256 * 1024


@dataclass(frozen=True)
class Release:
    version: str
    notes_url: str
    installer_url: str
    size: int


def parse_version(tag: str) -> tuple[int, ...] | None:
    match = VERSION_RE.match(tag.strip())
    return tuple(int(p) for p in match.group(1).split(".")) if match else None


def check_latest(current: str, opener=urllib.request.urlopen) -> Release | None:
    """A versão publicada mais nova, se for maior que a atual; None em qualquer problema."""
    try:
        with opener(LATEST_API, timeout=15) as resp:
            data = json.loads(resp.read())
        latest = parse_version(data["tag_name"])
        if latest is None or latest <= (parse_version(current) or (0,)):
            return None
        asset = next(a for a in data.get("assets", []) if ASSET_RE.match(a.get("name", "")))
        return Release(".".join(map(str, latest)), data.get("html_url", ""),
                       asset["browser_download_url"], int(asset.get("size") or 0))
    except (OSError, ValueError, KeyError, StopIteration, TypeError):
        log.info("verificação de nova versão indisponível agora")
        return None


def download_installer(release: Release, dest_dir: Path, opener=urllib.request.urlopen,
                       on_progress: Callable[[float], None] = lambda pct: None) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / release.installer_url.rsplit("/", 1)[-1]
    part = dest.with_name(dest.name + ".part")
    try:
        done = 0
        with opener(release.installer_url, timeout=60) as resp, open(part, "wb") as out:
            while chunk := resp.read(CHUNK):
                out.write(chunk)
                done += len(chunk)
                if release.size:
                    on_progress(min(done / release.size * 100, 100.0))
        if release.size and done != release.size:
            raise OSError(f"download incompleto ({done} de {release.size} bytes)")
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)
    return dest


def install_args(installer: Path) -> list[str]:
    """Instalação silenciosa (só a barra de progresso); o instalador reabre o programa no fim."""
    return [str(installer), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS",
            "/FORCECLOSEAPPLICATIONS"]
