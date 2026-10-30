"""Pergunta "só este vídeo / ver a playlist" e janela de escolha dos vídeos."""

import queue
import threading
from typing import Callable, Literal

import customtkinter as ctk

from ytdl.downloader import fetch_playlist
from ytdl.errors import DownloadError
from ytdl.formats import format_duration
from ytdl.playlist import MIX_LIMIT, PLAYLIST_LIMIT, Playlist, PlaylistEntry
from ytdl.queue_model import Kind
from ytdl.tools import Tools

POLL_MS = 100
ERROR_COLOR = ("#c5221f", "#f28b82")
MUTED = ("gray35", "gray65")


def _center(win: ctk.CTkToplevel, master) -> None:
    win.update_idletasks()
    x = master.winfo_rootx() + (master.winfo_width() - win.winfo_width()) // 2
    y = master.winfo_rooty() + (master.winfo_height() - win.winfo_height()) // 2
    win.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def ask_playlist(master) -> Literal["video", "playlist", None]:
    """Modal: o link faz parte de uma playlist. Devolve a escolha (None = fechou)."""
    dialog = ctk.CTkToplevel(master)
    dialog.title("Playlist encontrada")
    dialog.resizable(False, False)
    choice: dict[str, str | None] = {"value": None}

    def pick(value):
        choice["value"] = value
        dialog.destroy()

    ctk.CTkLabel(dialog, text="Este vídeo faz parte de uma playlist.\nO que você quer baixar?",
                 justify="left").grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 14), sticky="w")
    ctk.CTkButton(dialog, text="Só este vídeo", fg_color=("gray75", "gray30"), text_color=("gray10", "gray90"),
                  command=lambda: pick("video")).grid(row=1, column=0, padx=(20, 8), pady=(0, 20))
    ctk.CTkButton(dialog, text="Ver a playlist", command=lambda: pick("playlist")).grid(
        row=1, column=1, padx=(0, 20), pady=(0, 20))
    _center(dialog, master)
    dialog.transient(master)
    dialog.after(50, dialog.grab_set)
    master.wait_window(dialog)
    return choice["value"]


class PlaylistWindow(ctk.CTkToplevel):
    def __init__(self, master, tools: Tools, url: str, playlist_id: str, preselect: str | None,
                 default_kind: Kind, on_add: Callable[[list[PlaylistEntry], Kind], None]):
        super().__init__(master)
        self.title("Playlist")
        self.geometry("620x560")
        self.minsize(520, 420)
        self.on_add, self.preselect = on_add, preselect
        self.events: queue.Queue = queue.Queue()
        self.vars: list[tuple[PlaylistEntry, ctk.BooleanVar]] = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.title_label = ctk.CTkLabel(self, text="Carregando a playlist…", anchor="w",
                                        font=ctk.CTkFont(size=15, weight="bold"), wraplength=580, justify="left")
        self.title_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 0))
        self.note = ctk.CTkLabel(self, text="", anchor="w", text_color=MUTED)
        self.note.grid(row=1, column=0, sticky="ew", padx=16)
        self.list = ctk.CTkScrollableFrame(self)
        self.list.grid(row=2, column=0, sticky="nsew", padx=16, pady=8)
        self.list.grid_columnconfigure(1, weight=1)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        bottom.grid_columnconfigure(2, weight=1)
        self.all_btn = ctk.CTkButton(bottom, text="Marcar todos", width=110, state="disabled",
                                     fg_color=("gray75", "gray30"), text_color=("gray10", "gray90"),
                                     command=self._toggle_all)
        self.all_btn.grid(row=0, column=0, padx=(0, 8))
        self.kind_switch = ctk.CTkSegmentedButton(bottom, values=["MP4", "MP3"])
        self.kind_switch.set("MP3" if default_kind == "audio" else "MP4")
        self.kind_switch.grid(row=0, column=1)
        self.add_btn = ctk.CTkButton(bottom, text="Adicionar à fila", state="disabled", command=self._add)
        self.add_btn.grid(row=0, column=3)

        threading.Thread(target=self._load, args=(tools, url, playlist_id), daemon=True).start()
        self.after(POLL_MS, self._poll)
        _center(self, master)
        self.transient(master)
        self.after(50, self.grab_set)

    def _load(self, tools: Tools, url: str, playlist_id: str) -> None:
        try:
            self.events.put(("loaded", fetch_playlist(tools, url, playlist_id)))
        except DownloadError as exc:
            self.events.put(("failed", exc.friendly.message))
        except Exception:
            self.events.put(("failed", "Não foi possível carregar a playlist. Tente atualizar o programa."))

    def _poll(self) -> None:
        if not self.winfo_exists():
            return
        try:
            while True:
                kind, payload = self.events.get_nowait()
                self._on_loaded(payload) if kind == "loaded" else self._on_failed(payload)
        except queue.Empty:
            pass
        self.after(POLL_MS, self._poll)

    def _on_failed(self, message: str) -> None:
        self.title_label.configure(text=message, text_color=ERROR_COLOR)
        self.add_btn.configure(text="Fechar", state="normal", command=self.destroy)

    def _on_loaded(self, playlist: Playlist) -> None:
        self.title_label.configure(text=playlist.title)
        if playlist.is_mix:
            self.note.configure(text=f"Mix do YouTube: mostrando os primeiros {MIX_LIMIT} vídeos.")
        elif playlist.truncated:
            self.note.configure(text=f"Mostrando os primeiros {PLAYLIST_LIMIT} vídeos.")
        for row, entry in enumerate(playlist.entries):
            var = ctk.BooleanVar(value=entry.available and entry.video_id == self.preselect)
            box = ctk.CTkCheckBox(self.list, text="", width=24, variable=var, command=self._refresh,
                                  state="normal" if entry.available else "disabled")
            box.grid(row=row, column=0, padx=(0, 6), pady=2)
            text = entry.title if entry.available else f"{entry.title} (indisponível)"
            meta = f"{entry.channel} · {format_duration(entry.duration)}" if entry.available else ""
            label = ctk.CTkLabel(self.list, text=text if not meta else f"{text}\n{meta}", anchor="w",
                                 justify="left", text_color=None if entry.available else MUTED)
            label.grid(row=row, column=1, sticky="ew", pady=2)
            if entry.available:
                label.bind("<Button-1>", lambda e, v=var: (v.set(not v.get()), self._refresh()))
            self.vars.append((entry, var))
        self.all_btn.configure(state="normal")
        self._refresh()

    def _selected(self) -> list[PlaylistEntry]:
        return [entry for entry, var in self.vars if var.get()]

    def _refresh(self) -> None:
        count = len(self._selected())
        self.add_btn.configure(text=f"Adicionar {count} à fila", state="normal" if count else "disabled")
        available = [v for e, v in self.vars if e.available]
        all_on = bool(available) and all(v.get() for v in available)
        self.all_btn.configure(text="Desmarcar todos" if all_on else "Marcar todos")

    def _toggle_all(self) -> None:
        available = [v for e, v in self.vars if e.available]
        target = not all(v.get() for v in available)
        for var in available:
            var.set(target)
        self._refresh()

    def _add(self) -> None:
        selected = self._selected()
        if selected:
            self.on_add(selected, "audio" if self.kind_switch.get() == "MP3" else "video")
        self.destroy()
