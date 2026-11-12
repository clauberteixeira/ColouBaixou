"""Linha do tempo com duas alças (início e fim do trecho) e a posição que está tocando."""

from typing import Callable, Literal

import customtkinter as ctk

Handle = Literal["start", "end"]
PAD = 12  # espaço para a alça não sair da borda
REACH = 14  # distância (px) em que o clique pega a alça
HEIGHT = 44
TRACK = ("#c9c9c9", "#4a4a4a")
SELECTED = "#1a73e8"
PLAYHEAD = ("#202020", "#f0f0f0")


def to_x(t: float, duration: float, width: int, pad: int = PAD) -> float:
    return pad + (t / duration if duration else 0) * (width - 2 * pad)


def to_time(x: float, duration: float, width: int, pad: int = PAD) -> float:
    span = max(width - 2 * pad, 1)
    return min(max((x - pad) / span, 0.0), 1.0) * duration


def pick_handle(x: float, start_x: float, end_x: float, reach: float = REACH) -> Handle | None:
    d_start, d_end = abs(x - start_x), abs(x - end_x)
    if min(d_start, d_end) > reach:
        return None
    if d_start == d_end:  # alças juntas: a do início só pode ir para a esquerda, a do fim para a direita
        return "start" if start_x > reach + PAD else "end"
    return "start" if d_start < d_end else "end"


def move_handle(which: Handle, t: float, start: int, end: int, duration: int) -> tuple[int, int]:
    """Novo (início, fim) em segundos inteiros; as alças não se cruzam e o trecho tem ao menos 1 s."""
    t = round(t)
    if which == "start":
        return min(max(t, 0), end - 1), end
    return start, max(min(t, duration), start + 1)


class Timeline(ctk.CTkCanvas):
    """on_change(início, fim, alça) ao arrastar; on_seek(tempo) ao clicar fora das alças."""

    def __init__(self, master, duration: int, on_change: Callable[[int, int, Handle], None],
                 on_seek: Callable[[float], None], bg: str):
        super().__init__(master, height=HEIGHT, highlightthickness=0, bg=bg, cursor="hand2")
        self.duration = max(duration, 1)
        self.start, self.end, self.playhead = 0, self.duration, 0.0
        self.on_change, self.on_seek = on_change, on_seek
        self.active: Handle = "start"  # a última alça mexida (as setas do teclado movem ela)
        self._dragging: Handle | None = None
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_dragging", None))

    def _color(self, pair) -> str:
        return pair[1] if ctk.get_appearance_mode() == "Dark" else pair[0]

    def _x(self, t: float) -> float:
        return to_x(t, self.duration, self.winfo_width())

    def draw(self) -> None:
        self.delete("all")
        w, mid = self.winfo_width(), HEIGHT // 2
        self.create_line(PAD, mid, w - PAD, mid, width=6, fill=self._color(TRACK), capstyle="round")
        x0, x1 = self._x(self.start), self._x(self.end)
        self.create_line(x0, mid, x1, mid, width=6, fill=SELECTED)
        px = self._x(self.playhead)
        self.create_line(px, mid - 14, px, mid + 14, width=2, fill=self._color(PLAYHEAD))
        for x in (x0, x1):
            self.create_rectangle(x - 6, mid - 13, x + 6, mid + 13, fill=SELECTED, outline="white", width=2)

    def set_range(self, start: int, end: int) -> None:
        self.start, self.end = start, end
        self.draw()

    def set_playhead(self, t: float) -> None:
        self.playhead = t
        self.draw()

    def nudge(self, step: int) -> None:
        """Setas do teclado: mexe 1 s a última alça usada."""
        t = (self.start if self.active == "start" else self.end) + step
        self.move(self.active, t)

    def move(self, which: Handle, t: float) -> None:
        start, end = move_handle(which, t, self.start, self.end, self.duration)
        if (start, end) != (self.start, self.end):
            self.set_range(start, end)
            self.on_change(start, end, which)

    def _press(self, event) -> None:
        self.focus_set()
        self._dragging = pick_handle(event.x, self._x(self.start), self._x(self.end))
        if self._dragging:
            self.active = self._dragging
        else:
            self.on_seek(to_time(event.x, self.duration, self.winfo_width()))

    def _drag(self, event) -> None:
        if self._dragging:
            self.move(self._dragging, to_time(event.x, self.duration, self.winfo_width()))
        else:
            self.on_seek(to_time(event.x, self.duration, self.winfo_width()))
