"""Janela de Configurações: pasta principal e atualização do motor de download."""

import queue
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from ytdl.config import Config, save_config
from ytdl.tools import Tools, update_ytdlp, ytdlp_version

POLL_MS = 100


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, tools: Tools | None, config: Config, on_saved: Callable[[Config], None]):
        super().__init__(master)
        self.title("Configurações")
        self.resizable(False, False)
        self.tools = tools
        self.config_data = config
        self.on_saved = on_saved
        self.events: queue.Queue = queue.Queue()
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Pasta principal", font=ctk.CTkFont(weight="bold"), anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 4))
        self.folder_entry = ctk.CTkEntry(self, width=380)
        self.folder_entry.grid(row=1, column=0, sticky="ew", padx=(16, 8))
        self._show_folder()
        ctk.CTkButton(self, text="Escolher…", width=130, command=self._choose).grid(row=1, column=1, padx=(0, 16))

        ctk.CTkLabel(self, text="Motor de download", font=ctk.CTkFont(weight="bold"), anchor="w").grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(20, 4))
        self.version_label = ctk.CTkLabel(self, text="Versão: …", anchor="w")
        self.version_label.grid(row=3, column=0, sticky="ew", padx=16)
        self.update_btn = ctk.CTkButton(self, text="Atualizar agora", width=130, command=self._update)
        self.update_btn.grid(row=3, column=1, padx=(0, 16))
        self.update_status = ctk.CTkLabel(self, text="", anchor="w")
        self.update_status.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 16))

        if tools:
            self._background(lambda: self.events.put(("version", ytdlp_version(tools.ytdlp))))
        else:
            self.update_btn.configure(state="disabled")
            self.version_label.configure(text="Versão: preparando…")

        self.after(POLL_MS, self._poll)
        self._center_on(master)
        self.transient(master)
        self.after(50, self.grab_set)  # o Toplevel precisa estar visível antes do grab

    def _center_on(self, master) -> None:
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _show_folder(self) -> None:
        self.folder_entry.configure(state="normal")
        self.folder_entry.delete(0, "end")
        self.folder_entry.insert(0, str(self.config_data.base_dir))
        self.folder_entry.configure(state="readonly")

    def _choose(self) -> None:
        chosen = filedialog.askdirectory(parent=self, initialdir=self.config_data.base_dir,
                                         title="Escolha a pasta principal")
        if not chosen:
            return
        self.config_data = Config(base_dir=Path(chosen))
        save_config(self.config_data)
        self._show_folder()
        self.on_saved(self.config_data)

    def _update(self) -> None:
        self.update_btn.configure(state="disabled")
        self.update_status.configure(text="Atualizando…")

        def work():
            try:
                self.events.put(("updated", update_ytdlp(self.tools.ytdlp)))
            except Exception:
                self.events.put(("update_failed", None))

        self._background(work)

    def _background(self, fn) -> None:
        threading.Thread(target=fn, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "version":
                    self.version_label.configure(text=f"Versão: {payload}")
                elif kind == "updated":
                    self.version_label.configure(text=f"Versão: {payload}")
                    self.update_status.configure(text=f"Atualizado: {payload}")
                    self.update_btn.configure(state="normal")
                elif kind == "update_failed":
                    self.update_status.configure(text="Sem conexão. Tente mais tarde.")
                    self.update_btn.configure(state="normal")
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(POLL_MS, self._poll)
