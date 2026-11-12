"""Login opcional no YouTube pela sessão do Firefox (contra o bloqueio "não sou um robô").

O motor de download lê o login direto do Firefox (o Chrome e o Edge protegem o deles e não
deixam). Aqui só conferimos se há login do YouTube; nenhum valor é lido nem guardado.
"""

import os
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

Status = Literal["no_firefox", "no_login", "ok"]
LOGIN_COOKIES = ("SAPISID", "__Secure-3PSID", "LOGIN_INFO")
FIREFOX_DOWNLOAD = "https://www.mozilla.org/pt-BR/firefox/new/"
YOUTUBE_LOGIN = "https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/"


STORE_PROFILES = r"Packages\Mozilla.Firefox_n80bbvh6b1yt2\LocalCache\Roaming\Mozilla\Firefox\Profiles"


def profiles_dirs() -> list[Path]:
    """Onde o motor procura: o Firefox normal e o da Microsoft Store."""
    return [Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles",
            Path(os.environ.get("LOCALAPPDATA", "")) / STORE_PROFILES]


def firefox_status(profiles: Path | None = None) -> Status:
    """Situação do login no perfil do Firefox usado por último (o mesmo que o motor usa)."""
    folders = [profiles] if profiles else profiles_dirs()
    dbs = sorted((db for folder in folders for db in folder.glob("*/cookies.sqlite")),
                 key=lambda p: p.stat().st_mtime)
    if not dbs:
        return "no_firefox"
    db = dbs[-1]
    with tempfile.TemporaryDirectory() as tmp:
        # cópia: com o Firefox aberto o arquivo fica travado (o -wal tem os logins mais recentes)
        for suffix in ("", "-wal"):
            source = db.with_name(db.name + suffix)
            if source.exists():
                shutil.copy(source, Path(tmp) / f"cookies.sqlite{suffix}")
        try:
            con = sqlite3.connect(Path(tmp) / "cookies.sqlite")
            try:
                marks = ",".join("?" * len(LOGIN_COOKIES))
                row = con.execute(f"SELECT 1 FROM moz_cookies WHERE host LIKE '%youtube.com' "
                                  f"AND name IN ({marks}) LIMIT 1", LOGIN_COOKIES).fetchone()
            finally:
                con.close()
        except sqlite3.Error:
            return "no_login"
    return "ok" if row else "no_login"


def firefox_exe() -> Path | None:
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")):
        if base and (exe := Path(base) / "Mozilla Firefox" / "firefox.exe").exists():
            return exe
    store = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps" / "firefox.exe"  # atalho da Store
    return store if store.exists() else None


def open_in_firefox(url: str) -> bool:
    exe = firefox_exe()
    if not exe:
        return False
    subprocess.Popen([str(exe), url])
    return True
