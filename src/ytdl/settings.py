"""Janela de Configurações: conta do YouTube, atualizações e "sobre". (A pasta fica na tela principal.)"""

import queue
import threading
import webbrowser
from typing import Callable

import customtkinter as ctk

from ytdl.login import FIREFOX_DOWNLOAD, YOUTUBE_LOGIN, firefox_status, install_firefox, open_in_firefox
from ytdl.about import APP_NAME, AUTHOR, AUTHOR_URL, GUIDE_URL, ISSUES_URL, REPO_URL, VERSION
from ytdl.tools import Tools, ytdlp_version
from ytdl.updater import Release
from ytdl.windowing import center_on_screen

POLL_MS = 100
OK_COLOR = ("#188038", "#81c995")
MUTED = ("gray35", "gray65")
WARN_COLOR = ("#b06000", "#fdd663")
LOGIN_TEXT = {
    "no_firefox": ("O login usa o Firefox, que não está instalado. Clique em Instalar o Firefox: ele instala "
                   "sozinho e já abre o login do Google.", WARN_COLOR),
    "no_login": ("Falta entrar na conta. Clique em Entrar com a conta Google e faça o login na janela do Firefox.",
                 WARN_COLOR),
    "ok": ("✔ Conta do YouTube encontrada no Firefox.", OK_COLOR),
}
LOGIN_BUTTON = {"no_firefox": "Instalar o Firefox", "no_login": "Entrar com a conta Google",
                "ok": "Entrar com outra conta Google"}
WATCH_MS = 3000  # depois de abrir o login, confere sozinho a cada 3 s
GRAY = ("gray75", "gray30")
GRAY_HOVER = ("gray65", "gray40")


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, tools: Tools | None, release: Release | None = None,
                 on_update: Callable[[], None] | None = None, login: bool = False,
                 on_login: Callable[[bool], None] = lambda on: None):
        super().__init__(master)
        self.title("Configurações")
        self.resizable(False, False)
        self.events: queue.Queue = queue.Queue()
        self.grid_columnconfigure(0, weight=1)
        bold = ctk.CTkFont(weight="bold")

        # conta do YouTube
        self.on_login = on_login
        account = ctk.CTkFrame(self, fg_color="transparent")
        account.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 8))
        account.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(account, text="Conta do YouTube", font=bold, anchor="w").grid(row=0, column=0, sticky="ew")
        self.login_switch = ctk.CTkSwitch(account, text="Usar a conta do YouTube aberta no Firefox",
                                          command=self._toggle_login)
        if login:
            self.login_switch.select()
        self.login_switch.grid(row=1, column=0, sticky="w", pady=(4, 2))
        ctk.CTkLabel(account, text="Evita o bloqueio \"não sou um robô\" do YouTube. Use uma conta secundária, "
                                   "criada só para isso: o YouTube pode suspender a conta usada assim.",
                     text_color=MUTED, anchor="w", justify="left", wraplength=520).grid(row=2, column=0, sticky="ew")
        self.login_label = ctk.CTkLabel(account, text="", anchor="w", justify="left", wraplength=520)
        self.login_label.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        actions = ctk.CTkFrame(account, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.login_btn = ctk.CTkButton(actions, text="", width=230, command=self._login_action)
        self.login_btn.grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(actions, text="Verificar de novo", width=140, fg_color=GRAY, text_color=("gray10", "gray90"),
                      hover_color=GRAY_HOVER, command=self._check_login).grid(row=0, column=1)
        self._login_status = "no_firefox"
        self._login_events: queue.Queue = queue.Queue()
        self._watching = False
        self._check_login()

        # atualizações
        ctk.CTkLabel(self, text="Atualizações", font=bold, anchor="w").grid(
            row=10, column=0, columnspan=2, sticky="ew", padx=16, pady=(12, 4))
        if release:
            text, color = f"Programa: versão {VERSION} · nova versão {release.version} disponível", None
        else:
            text, color = f"Programa: versão {VERSION} · ✔ você está na versão mais recente", OK_COLOR
        ctk.CTkLabel(self, text=text, anchor="w", text_color=color).grid(row=11, column=0, sticky="ew", padx=16)
        if release and on_update:
            ctk.CTkButton(self, text="Atualizar agora", width=150,
                          command=lambda: (self.destroy(), on_update())).grid(row=11, column=1, padx=(0, 16))
        self.engine_label = ctk.CTkLabel(self, text="Motor de download: …", anchor="w", text_color=MUTED)
        self.engine_label.grid(row=12, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 0))

        # sobre
        ctk.CTkLabel(self, text="Sobre", font=bold, anchor="w").grid(
            row=13, column=0, columnspan=2, sticky="ew", padx=16, pady=(20, 4))
        about = ctk.CTkFrame(self, fg_color="transparent")
        about.grid(row=14, column=0, columnspan=2, sticky="ew", padx=16)
        ctk.CTkLabel(about, text=f"{APP_NAME} {VERSION} · Desenvolvido por ", anchor="w").grid(row=0, column=0)
        author = ctk.CTkLabel(about, text=AUTHOR, anchor="w", cursor="hand2", text_color=("#1a73e8", "#8ab4f8"))
        author.grid(row=0, column=1)
        author.bind("<Button-1>", lambda e: webbrowser.open(AUTHOR_URL))
        links = ctk.CTkFrame(self, fg_color="transparent")
        links.grid(row=15, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 16))
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

    def _check_login(self) -> None:
        self._login_status = firefox_status()
        text, color = LOGIN_TEXT[self._login_status]
        self.login_label.configure(text=text, text_color=color)
        self.login_btn.configure(text=LOGIN_BUTTON[self._login_status], state="normal")

    def _login_action(self) -> None:
        if self._login_status != "no_firefox":
            self._open_login()
            return
        self.login_btn.configure(state="disabled")
        self.login_label.configure(text="Instalando o Firefox… leva 1 ou 2 minutos. Não feche esta janela.",
                                   text_color=MUTED)
        threading.Thread(target=lambda: self._login_events.put(install_firefox()), daemon=True).start()
        self.after(500, self._wait_install)

    def _wait_install(self) -> None:
        if not self.winfo_exists():
            return
        try:
            installed = self._login_events.get_nowait()
        except queue.Empty:
            self.after(500, self._wait_install)
            return
        self._check_login()
        if installed and self._login_status != "no_firefox":
            self._open_login()
        else:
            webbrowser.open(FIREFOX_DOWNLOAD)
            self.login_label.configure(text="Não deu para instalar sozinho. Abri a página do Firefox: instale por lá "
                                            "e depois clique em Verificar de novo.", text_color=WARN_COLOR)

    def _open_login(self) -> None:
        """Abre o login do Google no Firefox e fica conferindo até a conta aparecer."""
        if not open_in_firefox(YOUTUBE_LOGIN):
            webbrowser.open(FIREFOX_DOWNLOAD)
            return
        self.login_label.configure(text="Faça o login na janela do Firefox que abriu. Este aviso muda sozinho "
                                        "quando a conta for encontrada.", text_color=MUTED)
        if not self._watching:
            self._watching = True
            self.after(WATCH_MS, self._watch_login)

    def _watch_login(self) -> None:
        if not self.winfo_exists():
            return
        if firefox_status() != "ok":
            self.after(WATCH_MS, self._watch_login)
            return
        self._watching = False
        self._check_login()
        if not self.login_switch.get():  # quem fez o login quer usar a conta: liga sozinho
            self.login_switch.select()
            self.on_login(True)
        self.login_label.configure(text="✔ Conta encontrada. Pronto: o programa já está usando a conta.",
                                   text_color=OK_COLOR)

    def _toggle_login(self) -> None:
        self.on_login(bool(self.login_switch.get()))

    def _poll(self) -> None:
        if not self.winfo_exists():
            return
        try:
            version = self.events.get_nowait()
            self.engine_label.configure(text=f"Motor de download: versão {version} · ✔ atualizado automaticamente")
        except queue.Empty:
            self.after(POLL_MS, self._poll)
