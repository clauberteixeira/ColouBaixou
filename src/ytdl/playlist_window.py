"""Pergunta "só este vídeo / ver a playlist" e janela de escolha dos vídeos."""

import queue
import threading
from tkinter import ttk
from typing import Callable, Literal

import customtkinter as ctk

from ytdl.downloader import fetch_playlist
from ytdl.errors import DownloadError
from ytdl.formats import format_duration
from ytdl.playlist import MIX_LIMIT, PLAYLIST_LIMIT, Playlist, PlaylistEntry
from ytdl.queue_model import Kind
from ytdl.queue_view import style_tree
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
        self.entries: dict[str, PlaylistEntry] = {}
        self.checked: dict[str, bool] = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.title_label = ctk.CTkLabel(self, text="Carregando a playlist…", anchor="w",
                                        font=ctk.CTkFont(size=15, weight="bold"), wraplength=580, justify="left")
        self.title_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 0))
        self.note = ctk.CTkLabel(self, text="", anchor="w", text_color=MUTED)
        self.note.grid(row=1, column=0, sticky="ew", padx=16)
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, columns=("check", "title", "channel", "duration"), show="headings",
                                 style=style_tree(30), selectmode="none")
        for col, text, width, stretch in (("check", "", 34, False), ("title", "Título", 300, True),
                                          ("channel", "Canal", 140, False), ("duration", "Duração", 70, False)):
            self.tree.heading(col, text=text, anchor="w")
            self.tree.column(col, width=width, stretch=stretch, anchor="center" if col == "check" else "w")
        self.tree.tag_configure("unavailable", foreground="#8a8a8a")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        scroll = ctk.CTkScrollbar(frame, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns", pady=4)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<ButtonRelease-1>", self._on_click)

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
        for entry in playlist.entries:
            if entry.video_id in self.entries:  # o mesmo vídeo pode aparecer duas vezes numa playlist
                continue
            self.entries[entry.video_id] = entry
            self.checked[entry.video_id] = entry.available and entry.video_id == self.preselect
            title = entry.title if entry.available else f"{entry.title} (indisponível)"
            duration = format_duration(entry.duration) if entry.available else ""
            self.tree.insert("", "end", iid=entry.video_id, values=("", title, entry.channel, duration),
                             tags=() if entry.available else ("unavailable",))
            self._draw(entry.video_id)
        self.all_btn.configure(state="normal")
        self._refresh()

    def _draw(self, video_id: str) -> None:
        mark = ("☑" if self.checked[video_id] else "☐") if self.entries[video_id].available else ""
        self.tree.set(video_id, "check", mark)

    def set_checked(self, video_id: str, value: bool) -> None:
        if self.entries[video_id].available:
            self.checked[video_id] = value
            self._draw(video_id)
            self._refresh()

    def _on_click(self, event) -> None:
        row = self.tree.identify_row(event.y)
        if row:
            self.set_checked(row, not self.checked[row])

    def _selected(self) -> list[PlaylistEntry]:
        return [self.entries[v] for v, on in self.checked.items() if on]

    def _refresh(self) -> None:
        count = len(self._selected())
        self.add_btn.configure(text=f"Adicionar {count} à fila", state="normal" if count else "disabled")
        available = [v for v, e in self.entries.items() if e.available]
        all_on = bool(available) and all(self.checked[v] for v in available)
        self.all_btn.configure(text="Desmarcar todos" if all_on else "Marcar todos")

    def _toggle_all(self) -> None:
        available = [v for v, e in self.entries.items() if e.available]
        target = not all(self.checked[v] for v in available)
        for video_id in available:
            self.checked[video_id] = target
            self._draw(video_id)
        self._refresh()

    def _add(self) -> None:
        selected = self._selected()
        if selected:
            self.on_add(selected, "audio" if self.kind_switch.get() == "MP3" else "video")
        self.destroy()
