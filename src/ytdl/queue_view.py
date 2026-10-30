"""Lista da fila na tela principal.

Usa o Treeview nativo (ttk): com componentes desenhados do CustomTkinter, 500 itens
travavam a tela por ~40 s; com o Treeview, menos de 0,1 s.
"""

from tkinter import ttk
from typing import Callable

import customtkinter as ctk
from PIL import Image, ImageTk

from ytdl.progress import describe
from ytdl.queue_model import EDITABLE, FINISHED, Item, Status

TITLE_MAX = 60
ROW_THUMB = (56, 32)
KIND_LABEL = {"video": "MP4", "audio": "MP3"}
COLUMNS = ("check", "title", "channel", "kind", "status", "remove")
STYLE = "Colou.Treeview"


def status_text(item: Item) -> tuple[str, bool]:
    """Texto da situação e se é erro."""
    if item.status == Status.REVIEW:
        return "Em revisão", False
    if item.status == Status.QUEUED:
        return "Aguardando", False
    if item.status == Status.DOWNLOADING:
        return (describe(item.progress) if item.progress else "Iniciando…"), False
    if item.status == Status.DONE:
        return "✔ Concluído (clique para abrir)", False
    if item.status == Status.ERROR:
        return f"Erro: {item.error}", True
    return "Cancelado", False


def display_title(item: Item) -> str:
    if not item.title:
        link = f"youtu.be/{item.video_id}"
        return link if item.status in FINISHED else f"{link} (carregando…)"
    return item.title if len(item.title) <= TITLE_MAX else item.title[:TITLE_MAX - 1] + "…"


def row_values(item: Item) -> tuple[str, ...]:
    check = ("☑" if item.checked else "☐") if item.status == Status.REVIEW else ""
    kind = KIND_LABEL[item.kind] + (" ▾" if item.status in EDITABLE else "")
    return check, display_title(item), item.channel or "", kind, status_text(item)[0], "✕"


def row_tag(item: Item) -> str:
    if item.status == Status.ERROR:
        return "error"
    if item.status == Status.DONE:
        return "done"
    return "muted" if item.status == Status.CANCELLED else "normal"


def style_tree(row_height: int) -> str:
    """Cores do Treeview seguindo o tema claro/escuro do app."""
    dark = ctk.get_appearance_mode() == "Dark"
    bg, fg, head, sel = ("#2b2b2b", "#e6e6e6", "#333333", "#1f6aa5") if dark else \
        ("#ffffff", "#1a1a1a", "#e9e9e9", "#3a7ebf")
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(STYLE, background=bg, fieldbackground=bg, foreground=fg, rowheight=row_height,
                    borderwidth=0, font=("Segoe UI", 10))
    style.configure(f"{STYLE}.Heading", background=head, foreground=fg, relief="flat", font=("Segoe UI", 9, "bold"))
    style.map(STYLE, background=[("selected", sel)], foreground=[("selected", "#ffffff")])
    style.layout(STYLE, [("Treeview.treearea", {"sticky": "nswe"})])
    return STYLE


class QueueView(ctk.CTkFrame):
    def __init__(self, master, on_toggle: Callable[[int, bool], None], on_kind: Callable[[int, str], None],
                 on_remove: Callable[[int], None], on_open: Callable[[int], None]):
        super().__init__(master)
        self.on_toggle, self.on_kind, self.on_remove, self.on_open = on_toggle, on_kind, on_remove, on_open
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.items: dict[int, Item] = {}
        self.thumbs: dict[str, ImageTk.PhotoImage] = {}

        self.tree = ttk.Treeview(self, columns=COLUMNS, show="tree headings", style=style_tree(ROW_THUMB[1] + 8),
                                 selectmode="browse")
        headings = {"check": "", "title": "Título", "channel": "Canal", "kind": "Formato",
                    "status": "Situação", "remove": ""}
        widths = {"check": 30, "title": 230, "channel": 100, "kind": 70, "status": 270, "remove": 30}
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=ROW_THUMB[0] + 22, stretch=False)
        for col in COLUMNS:
            self.tree.heading(col, text=headings[col], anchor="w")
            stretch = col in ("title", "status")
            anchor = "center" if col in ("check", "remove") else "w"
            self.tree.column(col, width=widths[col], stretch=stretch, anchor=anchor, minwidth=widths[col] // 2)
        self.tree.tag_configure("error", foreground="#e05a50")
        self.tree.tag_configure("done", foreground="#3faa63")
        self.tree.tag_configure("muted", foreground="#8a8a8a")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        scroll = ctk.CTkScrollbar(self, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns", pady=4)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<ButtonRelease-1>", self._on_click)
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Delete>", self._on_delete_key)

        self.empty = ctk.CTkLabel(self, text="Nenhum item na fila. Cole um ou vários links acima.",
                                  text_color=("gray35", "gray65"), fg_color="transparent")

    # --- desenho ---------------------------------------------------------

    def _apply(self, item: Item) -> None:
        iid = str(item.id)
        kwargs = {"values": row_values(item), "tags": (row_tag(item),)}
        if item.video_id in self.thumbs:
            kwargs["image"] = self.thumbs[item.video_id]
        if self.tree.exists(iid):
            self.tree.item(iid, **kwargs)
        else:
            self.tree.insert("", "end", iid=iid, text="", **kwargs)

    def render(self, items: list[Item]) -> None:
        self.items = {i.id: i for i in items}
        for iid in self.tree.get_children():
            if int(iid) not in self.items:
                self.tree.delete(iid)
        for position, item in enumerate(items):
            self._apply(item)
            if self.tree.index(str(item.id)) != position:
                self.tree.move(str(item.id), "", position)
        if items:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")

    def update_item(self, item: Item) -> None:
        self.items[item.id] = item
        if self.tree.exists(str(item.id)):
            self._apply(item)

    def set_thumb(self, video_id: str, image: Image.Image) -> None:
        self.thumbs[video_id] = ImageTk.PhotoImage(image)
        for item in self.items.values():
            if item.video_id == video_id and self.tree.exists(str(item.id)):
                self.tree.item(str(item.id), image=self.thumbs[video_id])

    # --- cliques ---------------------------------------------------------

    def _hit(self, event) -> tuple[Item | None, str]:
        row = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)  # "#0", "#1"…
        if not row:
            return None, ""
        index = int(column[1:]) - 1
        name = COLUMNS[index] if 0 <= index < len(COLUMNS) else ""
        return self.items.get(int(row)), name

    def _on_click(self, event) -> None:
        item, column = self._hit(event)
        if item is None:
            return
        if column == "check" and item.status == Status.REVIEW:
            self.on_toggle(item.id, not item.checked)
        elif column == "kind" and item.status in EDITABLE:
            self.on_kind(item.id, "audio" if item.kind == "video" else "video")
        elif column == "remove":
            self.on_remove(item.id)
        elif column == "status" and item.status == Status.DONE:
            self.on_open(item.id)

    def _on_double(self, event) -> None:
        item, column = self._hit(event)
        if item and item.status == Status.DONE and column not in ("remove", "kind", "check"):
            self.on_open(item.id)

    def _on_delete_key(self, _event) -> None:
        for iid in self.tree.selection():
            self.on_remove(int(iid))
