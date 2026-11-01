"""Pergunta "só este vídeo / ver a playlist" e janela de escolha dos vídeos."""

import io
import queue
import threading
from tkinter import ttk
from typing import Callable, Literal

import customtkinter as ctk
from PIL import Image, ImageTk

from ytdl.downloader import fetch_playlist
from ytdl.errors import DownloadError
from ytdl.formats import format_duration
from ytdl.images import CHECK_SIZE, GAP, Check, row_image
from ytdl.net import urlopen
from ytdl.playlist import MIX_LIMIT, PLAYLIST_LIMIT, Playlist, PlaylistEntry, thumb_url
from ytdl.queue_model import Kind
from ytdl.queue_view import style_tree
from ytdl.tools import Tools
from ytdl.windowing import app_size, center_on_screen

POLL_MS = 100
THUMB = (64, 36)
DONE_LABEL = "✔ Já baixado"
ERROR_COLOR = ("#c5221f", "#f28b82")
MUTED = ("gray35", "gray65")
GRAY = ("gray75", "gray30")
GRAY_HOVER = ("gray65", "gray40")


def entry_state(entry: PlaylistEntry, checked: bool, downloaded: bool) -> Check:
    if not entry.available or downloaded:
        return "disabled"
    return "on" if checked else "off"


def selection_summary(total: int, selected: int, downloaded: int) -> str:
    parts = [f"{total} vídeo{'s' if total != 1 else ''}",
             "nenhum selecionado" if not selected else f"{selected} selecionado{'s' if selected != 1 else ''}"]
    if downloaded:
        parts.append(f"{downloaded} já baixado{'s' if downloaded != 1 else ''}")
    return " · ".join(parts)


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
    ctk.CTkButton(dialog, text="Só este vídeo", fg_color=GRAY, text_color=("gray10", "gray90"),
                  hover_color=GRAY_HOVER, command=lambda: pick("video")).grid(row=1, column=0, padx=(20, 8), pady=(0, 20))
    ctk.CTkButton(dialog, text="Ver a playlist", command=lambda: pick("playlist")).grid(
        row=1, column=1, padx=(0, 20), pady=(0, 20))
    center_on_screen(dialog)
    dialog.transient(master)
    dialog.after(50, dialog.grab_set)
    master.wait_window(dialog)
    return choice["value"]


class PlaylistWindow(ctk.CTkToplevel):
    def __init__(self, master, tools: Tools, url: str, playlist_id: str, preselect: str | None,
                 default_kind: Kind, on_add: Callable[[list[PlaylistEntry], Kind], None],
                 is_downloaded: Callable[[PlaylistEntry, Kind], bool] = lambda entry, kind: False,
                 size: tuple[int, int] | None = None,
                 on_close: Callable[[str, tuple[int, int]], None] = lambda state, size: None):
        super().__init__(master)
        self.title("Playlist")
        self.minsize(600, 440)
        self.on_add, self.preselect, self.is_downloaded = on_add, preselect, is_downloaded
        self.on_close = on_close
        self.events: queue.Queue = queue.Queue()
        self.entries: dict[str, PlaylistEntry] = {}
        self.checked: dict[str, bool] = {}
        self.downloaded: dict[str, bool] = {}
        self.thumbs: dict[str, Image.Image] = {}
        self._images: dict[tuple, ImageTk.PhotoImage] = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.title_label = ctk.CTkLabel(self, text="Carregando a playlist…", anchor="w",
                                        font=ctk.CTkFont(size=16, weight="bold"), wraplength=720, justify="left")
        self.title_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 2))
        self.note = ctk.CTkLabel(self, text="", anchor="w", text_color=MUTED)
        self.note.grid(row=1, column=0, sticky="ew", padx=16)

        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, columns=("title", "channel", "duration", "state"), show="tree headings",
                                 style=style_tree(THUMB[1] + 10), selectmode="none")
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=CHECK_SIZE + GAP + THUMB[0] + 28, stretch=False)
        for col, text, width, stretch in (("title", "Título", 300, True), ("channel", "Canal", 140, False),
                                          ("duration", "Duração", 70, False), ("state", "", 110, False)):
            self.tree.heading(col, text=text, anchor="w")
            self.tree.column(col, width=width, stretch=stretch, anchor="w", minwidth=width // 2)
        self.tree.tag_configure("disabled", foreground="#8a8a8a")
        self.tree.tag_configure("done", foreground="#3faa63")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        scroll = ctk.CTkScrollbar(frame, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns", pady=4)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<ButtonRelease-1>", self._on_click)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        bottom.grid_columnconfigure(2, weight=1)
        self.all_btn = ctk.CTkButton(bottom, text="Marcar todos", width=130, state="disabled", fg_color=GRAY,
                                     text_color=("gray10", "gray90"), hover_color=GRAY_HOVER, command=self._toggle_all)
        self.all_btn.grid(row=0, column=0, padx=(0, 8))
        self.kind_switch = ctk.CTkSegmentedButton(bottom, values=["MP4", "MP3"], command=lambda v: self._on_kind())
        self.kind_switch.set("MP3" if default_kind == "audio" else "MP4")
        self.kind_switch.grid(row=0, column=1)
        self.summary = ctk.CTkLabel(bottom, text="", text_color=MUTED)
        self.summary.grid(row=0, column=2, padx=12, sticky="e")
        self.add_btn = ctk.CTkButton(bottom, text="Adicionar à fila", width=170, state="disabled", command=self._add)
        self.add_btn.grid(row=0, column=3)

        threading.Thread(target=self._load, args=(tools, url, playlist_id), daemon=True).start()
        self.after(POLL_MS, self._poll)
        center_on_screen(self, *(size or (760, 600)))
        self.protocol("WM_DELETE_WINDOW", self.destroy)  # sem isso, o X fecha direto pelo Tk
        self.transient(master)
        self.after(50, self.grab_set)

    def destroy(self) -> None:
        self.on_close(self.state(), app_size(self))
        super().destroy()

    # --- carregamento (threads só fazem events.put) ------------------------

    def _load(self, tools: Tools, url: str, playlist_id: str) -> None:
        try:
            playlist = fetch_playlist(tools, url, playlist_id)
        except DownloadError as exc:
            self.events.put(("failed", exc.friendly.message))
            return
        except Exception:
            self.events.put(("failed", "Não foi possível carregar a playlist. Tente atualizar o programa."))
            return
        self.events.put(("loaded", playlist))
        for entry in playlist.entries:  # miniaturas, uma por vez
            try:
                with urlopen(thumb_url(entry.video_id), timeout=15) as resp:
                    self.events.put(("thumb", (entry.video_id, Image.open(io.BytesIO(resp.read())).convert("RGB"))))
            except Exception:
                pass

    def _poll(self) -> None:
        if not self.winfo_exists():
            return
        try:
            while True:
                kind, payload = self.events.get_nowait()
                getattr(self, f"_on_{kind}")(payload)
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
        else:
            self.note.configure(text="Clique nos vídeos para marcar ou desmarcar.")
        for entry in playlist.entries:
            if entry.video_id in self.entries:  # o mesmo vídeo pode aparecer duas vezes numa playlist
                continue
            self.entries[entry.video_id] = entry
            self.checked[entry.video_id] = entry.video_id == self.preselect
            title = entry.title if entry.available else f"{entry.title} (indisponível)"
            duration = format_duration(entry.duration) if entry.available else ""
            self.tree.insert("", "end", iid=entry.video_id, values=(title, entry.channel, duration, ""))
        self.all_btn.configure(state="normal")
        self._on_kind()

    def _on_thumb(self, payload) -> None:
        video_id, image = payload
        self.thumbs[video_id] = image
        if self.tree.exists(video_id):
            self._draw(video_id)

    # --- estado das linhas -------------------------------------------------

    @property
    def kind(self) -> Kind:
        return "audio" if self.kind_switch.get() == "MP3" else "video"

    def _state(self, video_id: str) -> Check:
        return entry_state(self.entries[video_id], self.checked[video_id], self.downloaded[video_id])

    def _draw(self, video_id: str) -> None:
        state = self._state(video_id)
        key = (video_id if video_id in self.thumbs else None, state)
        if key not in self._images:
            self._images[key] = ImageTk.PhotoImage(row_image(self.thumbs.get(video_id), state, THUMB))
        label = DONE_LABEL if self.downloaded[video_id] else ""
        tag = "done" if self.downloaded[video_id] else "disabled" if state == "disabled" else ""
        self.tree.item(video_id, image=self._images[key], tags=(tag,) if tag else ())
        self.tree.set(video_id, "state", label)

    def _on_kind(self) -> None:
        """Trocou MP4/MP3: o que já foi baixado nesse formato fica bloqueado."""
        for video_id, entry in self.entries.items():
            self.downloaded[video_id] = entry.available and self.is_downloaded(entry, self.kind)
            if self.downloaded[video_id]:
                self.checked[video_id] = False
            self._draw(video_id)
        self._refresh()

    def _selectable(self) -> list[str]:
        return [v for v, e in self.entries.items() if e.available and not self.downloaded[v]]

    def set_checked(self, video_id: str, value: bool) -> None:
        if video_id in self._selectable():
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
        self.add_btn.configure(text=f"Adicionar {count} à fila" if count else "Adicionar à fila",
                               state="normal" if count else "disabled")
        selectable = self._selectable()
        all_on = bool(selectable) and all(self.checked[v] for v in selectable)
        self.all_btn.configure(text="Desmarcar todos" if all_on else "Marcar todos")
        self.summary.configure(text=selection_summary(len(self.entries), count, sum(self.downloaded.values())))

    def _toggle_all(self) -> None:
        selectable = self._selectable()
        target = not all(self.checked[v] for v in selectable)
        for video_id in selectable:
            self.checked[video_id] = target
            self._draw(video_id)
        self._refresh()

    def _add(self) -> None:
        selected = self._selected()
        if selected:
            self.on_add(selected, self.kind)
        self.destroy()

