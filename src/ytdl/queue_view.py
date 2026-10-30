"""Lista da fila na tela principal."""

from typing import Callable

import customtkinter as ctk

from ytdl.progress import describe
from ytdl.queue_model import EDITABLE, FINISHED, Item, Status

TITLE_MAX = 60
ROW_THUMB = (56, 32)
KIND_LABEL = {"video": "MP4", "audio": "MP3"}
LABEL_KIND = {v: k for k, v in KIND_LABEL.items()}
ERROR_COLOR = ("#c5221f", "#f28b82")
OK_COLOR = ("#188038", "#81c995")
MUTED = ("gray35", "gray65")


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


class QueueRow(ctk.CTkFrame):
    def __init__(self, master, view: "QueueView", item: Item):
        super().__init__(master, fg_color="transparent")
        self.view, self.item_id, self.video_id = view, item.id, item.video_id
        self.grid_columnconfigure(2, weight=1)

        self.check_var = ctk.BooleanVar(value=item.checked)
        self.check = ctk.CTkCheckBox(self, text="", width=24, variable=self.check_var,
                                     command=lambda: view.on_toggle(self.item_id, self.check_var.get()))
        self.thumb = ctk.CTkLabel(self, text="", width=ROW_THUMB[0], height=ROW_THUMB[1],
                                  fg_color=("gray80", "gray25"), corner_radius=3)
        self.thumb.grid(row=0, column=1, rowspan=2, padx=(0, 8), pady=4)
        self.title = ctk.CTkLabel(self, text="", anchor="w")
        self.title.grid(row=0, column=2, sticky="ew")
        self.status = ctk.CTkLabel(self, text="", anchor="w", font=ctk.CTkFont(size=12))
        self.status.grid(row=1, column=2, sticky="ew")
        self.status.bind("<Button-1>", lambda e: view.on_open(self.item_id))
        self.bar = ctk.CTkProgressBar(self, height=6)
        self.kind = ctk.CTkOptionMenu(self, values=list(LABEL_KIND), width=74,
                                      command=lambda v: view.on_kind(self.item_id, LABEL_KIND[v]))
        self.kind.grid(row=0, column=3, rowspan=2, padx=8)
        ctk.CTkButton(self, text="✕", width=28, height=28, fg_color="transparent",
                      text_color=MUTED, hover_color=("gray80", "gray30"),
                      command=lambda: view.on_remove(self.item_id)).grid(row=0, column=4, rowspan=2)
        self.update_from(item)

    def update_from(self, item: Item) -> None:
        if item.status == Status.REVIEW:
            self.check.grid(row=0, column=0, rowspan=2, padx=(0, 4))
            self.check_var.set(item.checked)
        else:
            self.check.grid_remove()
        self.title.configure(text=display_title(item))
        text, error = status_text(item)
        color = ERROR_COLOR if error else OK_COLOR if item.status == Status.DONE else MUTED
        self.status.configure(text=text, text_color=color, cursor="hand2" if item.status == Status.DONE else "")
        if item.status == Status.DOWNLOADING and item.progress and item.progress.percent is not None:
            self.bar.grid(row=2, column=2, sticky="ew", pady=(0, 4))
            self.bar.set(item.progress.percent / 100)
        elif item.status == Status.DOWNLOADING:
            self.bar.grid(row=2, column=2, sticky="ew", pady=(0, 4))
        else:
            self.bar.grid_remove()
        self.kind.set(KIND_LABEL[item.kind])
        self.kind.configure(state="normal" if item.status in EDITABLE else "disabled")
        image = self.view.thumbs.get(self.video_id)
        if image:
            self.thumb.configure(image=image)


class QueueView(ctk.CTkScrollableFrame):
    def __init__(self, master, on_toggle: Callable[[int, bool], None], on_kind: Callable[[int, str], None],
                 on_remove: Callable[[int], None], on_open: Callable[[int], None]):
        super().__init__(master)
        self.on_toggle, self.on_kind, self.on_remove, self.on_open = on_toggle, on_kind, on_remove, on_open
        self.grid_columnconfigure(0, weight=1)
        self.rows: dict[int, QueueRow] = {}
        self.thumbs: dict[str, ctk.CTkImage] = {}
        self.empty = ctk.CTkLabel(self, text="Nenhum item na fila. Cole um ou vários links acima.", text_color=MUTED)

    def render(self, items: list[Item]) -> None:
        alive = {i.id for i in items}
        for item_id in list(self.rows):
            if item_id not in alive:
                self.rows.pop(item_id).destroy()
        for position, item in enumerate(items):
            row = self.rows.get(item.id)
            if row is None:
                row = self.rows[item.id] = QueueRow(self, self, item)
            else:
                row.update_from(item)
            row.grid(row=position, column=0, sticky="ew", pady=1)
        if items:
            self.empty.grid_remove()
        else:
            self.empty.grid(row=0, column=0, pady=24)

    def update_item(self, item: Item) -> None:
        if row := self.rows.get(item.id):
            row.update_from(item)

    def set_thumb(self, video_id: str, image: ctk.CTkImage) -> None:
        self.thumbs[video_id] = image
        for row in self.rows.values():
            if row.video_id == video_id:
                row.thumb.configure(image=image)
