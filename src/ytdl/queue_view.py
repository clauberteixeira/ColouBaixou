"""Lista da fila na tela principal.

Usa o Treeview nativo (ttk): com componentes desenhados do CustomTkinter, 500 itens
travavam a tela por ~40 s; com o Treeview, menos de 0,1 s.
"""

import tkinter
from tkinter import ttk
from typing import Callable

import customtkinter as ctk
from PIL import Image, ImageTk

from ytdl.images import CHECK_SIZE, GAP, Check, row_image
from ytdl.progress import describe
from ytdl.queue_model import ACTIVE, EDITABLE, FINISHED, Item, Status

TITLE_MAX = 60
ROW_THUMB = (56, 32)
KIND_LABEL = {"video": "MP4", "audio": "MP3"}
COLUMNS = ("title", "channel", "kind", "status", "remove")
FIXED_COLUMNS = ("#0", "channel", "kind", "remove")
STATUS_WIDTH = 270  # cabe "62% · 48 MB de 77 MB · faltam ~9s"
MIN_FLEXIBLE = 150  # título + situação
STYLE = "Colou.Treeview"


def status_text(item: Item) -> tuple[str, bool]:
    """Texto da situação e se é erro."""
    if item.status == Status.REVIEW:
        return "Em revisão", False
    if item.status == Status.QUEUED:
        return "Aguardando", False
    if item.cancelling and item.status == Status.DOWNLOADING:
        return "Cancelando…", False
    if item.status == Status.DOWNLOADING:
        return (describe(item.progress) if item.progress else "Iniciando…"), False
    if item.status == Status.DONE:
        done = "✔ Já baixado antes" if item.previously else "✔ Concluído"
        return f"{done} (clique para abrir)", False
    if item.status == Status.ERROR:
        return f"Erro: {item.error}", True
    return "Cancelado", False


def display_title(item: Item) -> str:
    if not item.title:
        link = f"youtu.be/{item.video_id}"
        return link if item.status in FINISHED else f"{link} (carregando…)"
    return item.title if len(item.title) <= TITLE_MAX else item.title[:TITLE_MAX - 1] + "…"


def row_values(item: Item) -> tuple[str, ...]:
    kind = KIND_LABEL[item.kind] + (" ▾" if item.status in EDITABLE else "")
    return display_title(item), item.channel or "", kind, status_text(item)[0], "✕"


def row_check(item: Item) -> Check | None:
    """Caixinha só enquanto o item está em revisão."""
    if item.status != Status.REVIEW:
        return None
    return "on" if item.checked else "off"


def row_tag(item: Item) -> str:
    if item.status == Status.ERROR:
        return "error"
    if item.status == Status.DONE:
        return "done"
    return "muted" if item.status == Status.CANCELLED else "normal"


def menu_actions(item: Item) -> list[tuple[str, str]]:
    """Opções do botão direito: (texto, ação)."""
    actions = [("Remover da lista", "remove")]
    if item.status in ACTIVE and not item.cancelling:
        label = "Cancelar download" if item.status == Status.DOWNLOADING else "Cancelar"
        actions.insert(0, (label, "cancel"))
    return actions


def column_widths(total: int, fixed: int) -> tuple[int, int]:
    """Larguras do título e da situação: juntas ocupam o que sobra, para o ✕ não sair da tela.

    A situação fica com 60% até caber o progresso; com mais espaço, cada uma fica com metade.
    """
    free = max(total - fixed, MIN_FLEXIBLE)
    status = min(free * 3 // 5, max(STATUS_WIDTH, free // 2))
    return free - status, status


def _colors() -> tuple[str, str, str, str]:
    """Fundo, texto, cabeçalho e seleção, seguindo o tema claro/escuro do app."""
    if ctk.get_appearance_mode() == "Dark":
        return "#2b2b2b", "#e6e6e6", "#333333", "#1f6aa5"
    return "#ffffff", "#1a1a1a", "#e9e9e9", "#3a7ebf"


def style_tree(row_height: int) -> str:
    """Cores do Treeview seguindo o tema claro/escuro do app."""
    bg, fg, head, sel = _colors()
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
                 on_remove: Callable[[int], None], on_open: Callable[[int], None],
                 on_cancel: Callable[[int], None]):
        super().__init__(master)
        self.on_toggle, self.on_kind, self.on_remove, self.on_open = on_toggle, on_kind, on_remove, on_open
        self.on_cancel = on_cancel
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.items: dict[int, Item] = {}
        self.thumbs: dict[str, Image.Image] = {}
        self._images: dict[tuple, ImageTk.PhotoImage] = {}  # (video_id, caixinha) → imagem pronta

        self.tree = ttk.Treeview(self, columns=COLUMNS, show="tree headings", style=style_tree(ROW_THUMB[1] + 8),
                                 selectmode="browse")
        headings = {"title": "Título", "channel": "Canal", "kind": "Formato", "status": "Situação", "remove": ""}
        widths = {"title": 230, "channel": 100, "kind": 70, "status": 270, "remove": 30}
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=CHECK_SIZE + GAP + ROW_THUMB[0] + 28, stretch=False)
        for col in COLUMNS:
            self.tree.heading(col, text=headings[col], anchor="w")
            stretch = col in ("title", "status")
            anchor = "center" if col == "remove" else "w"
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
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Configure>", self._fit_columns)

        bg, fg, _, sel = _colors()
        self.menu = tkinter.Menu(self, tearoff=0, bg=bg, fg=fg, activebackground=sel,
                                 activeforeground="#ffffff", font=("Segoe UI", 10))

        self.empty = ctk.CTkLabel(self, text="Nenhum item na fila. Cole um ou vários links acima.",
                                  text_color=("gray35", "gray65"), fg_color="transparent")

    # --- desenho ---------------------------------------------------------

    def _image(self, item: Item) -> ImageTk.PhotoImage:
        key = (item.video_id if item.video_id in self.thumbs else None, row_check(item))
        if key not in self._images:
            self._images[key] = ImageTk.PhotoImage(row_image(self.thumbs.get(item.video_id), key[1], ROW_THUMB))
        return self._images[key]

    def _apply(self, item: Item) -> None:
        iid = str(item.id)
        kwargs = {"values": row_values(item), "tags": (row_tag(item),), "image": self._image(item)}
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

    def _fit_columns(self, event) -> None:
        fixed = sum(self.tree.column(column, "width") for column in FIXED_COLUMNS)
        title, status = column_widths(event.width, fixed)
        self.tree.column("title", width=title)
        self.tree.column("status", width=status)

    def update_item(self, item: Item) -> None:
        self.items[item.id] = item
        if self.tree.exists(str(item.id)):
            self._apply(item)

    def set_thumb(self, video_id: str, image: Image.Image) -> None:
        self.thumbs[video_id] = image
        for item in self.items.values():
            if item.video_id == video_id and self.tree.exists(str(item.id)):
                self.tree.item(str(item.id), image=self._image(item))

    # --- cliques ---------------------------------------------------------

    def _hit(self, event) -> tuple[Item | None, str]:
        row = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)  # "#0", "#1"…
        if not row:
            return None, ""
        index = int(column[1:]) - 1
        name = "check" if index < 0 else COLUMNS[index] if index < len(COLUMNS) else ""
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

    def _on_right_click(self, event) -> None:
        item, _ = self._hit(event)
        if item is None:
            return
        self.tree.selection_set(str(item.id))
        handlers = {"cancel": self.on_cancel, "remove": self.on_remove}
        self.menu.delete(0, "end")
        for label, action in menu_actions(item):
            self.menu.add_command(label=label, command=lambda run=handlers[action], item_id=item.id: run(item_id))
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _on_delete_key(self, _event) -> None:
        for iid in self.tree.selection():
            self.on_remove(int(iid))
