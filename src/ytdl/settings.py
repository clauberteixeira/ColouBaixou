"""Janela de Configurações: atualizações e "sobre". (A pasta fica na tela principal.)"""

import queue
import threading
import webbrowser
from typing import Callable

import customtkinter as ctk

from ytdl.about import APP_NAME, AUTHOR, AUTHOR_URL, GUIDE_URL, ISSUES_URL, REPO_URL, VERSION
from ytdl.tools import Tools, ytdlp_version
from ytdl.updater import Release
from ytdl.windowing import center_on_screen

POLL_MS = 100
OK_COLOR = ("#188038", "#81c995")
MUTED = ("gray35", "gray65")
GRAY = ("gray75", "gray30")
GRAY_HOVER = ("gray65", "gray40")


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, tools: Tools | None, release: Release | None = None,
                 on_update: Callable[[], None] | None = None):
        super().__init__(master)
        self.title("Configurações")
        self.resizable(False, False)
        self.events: queue.Queue = queue.Queue()
        self.grid_columnconfigure(0, weight=1)
        bold = ctk.CTkFont(weight="bold")

        # atualizações
        ctk.CTkLabel(self, text="Atualizações", font=bold, anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 4))
        if release:
            text, color = f"Programa: versão {VERSION} · nova versão {release.version} disponível", None
        else:
            text, color = f"Programa: versão {VERSION} · ✔ você está na versão mais recente", OK_COLOR
        ctk.CTkLabel(self, text=text, anchor="w", text_color=color).grid(row=1, column=0, sticky="ew", padx=16)
        if release and on_update:
            ctk.CTkButton(self, text="Atualizar agora", width=150,
                          command=lambda: (self.destroy(), on_update())).grid(row=1, column=1, padx=(0, 16))
        self.engine_label = ctk.CTkLabel(self, text="Motor de download: …", anchor="w", text_color=MUTED)
        self.engine_label.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 0))

        # sobre
        ctk.CTkLabel(self, text="Sobre", font=bold, anchor="w").grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(20, 4))
        about = ctk.CTkFrame(self, fg_color="transparent")
        about.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16)
        ctk.CTkLabel(about, text=f"{APP_NAME} {VERSION} · Desenvolvido por ", anchor="w").grid(row=0, column=0)
        author = ctk.CTkLabel(about, text=AUTHOR, anchor="w", cursor="hand2", text_color=("#1a73e8", "#8ab4f8"))
        author.grid(row=0, column=1)
        author.bind("<Button-1>", lambda e: webbrowser.open(AUTHOR_URL))
        links = ctk.CTkFrame(self, fg_color="transparent")
        links.grid(row=5, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 16))
        for column, (text, url) in enumerate((("Página do projeto", REPO_URL), ("Como usar", GUIDE_URL),
                                               ("Relatar um problema", ISSUES_URL))):
            ctk.CTkButton(links, text=text, width=150, fg_color=GRAY, text_color=("gray10", "gray90"),
                          hover_color=GRAY_HOVER, command=lambda u=url: webbrowser.open(u)).grid(
                row=0, column=column, padx=(0, 8))

        if tools:
            threading.Thread(target=lambda: self.events.put(ytdlp_version(tools.ytdlp)), daemon=True).start()
        self.after(POLL_MS, self._poll)
        center_on_screen(self)
        self.transient(master)
        self.after(50, self.grab_set)  # o Toplevel precisa estar visível antes do grab

    def _poll(self) -> None:
        if not self.winfo_exists():
            return
        try:
            version = self.events.get_nowait()
            self.engine_label.configure(text=f"Motor de download: versão {version} · ✔ atualizado automaticamente")
        except queue.Empty:
            self.after(POLL_MS, self._poll)
