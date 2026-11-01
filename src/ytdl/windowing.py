"""Abrir janelas centralizadas na tela (cabendo em telas pequenas)."""

import ctypes
import tkinter
from ctypes import wintypes

SPI_GETWORKAREA = 48
SM_CYCAPTION, SM_CXSIZEFRAME, SM_CYSIZEFRAME, SM_CXPADDEDBORDER = 4, 32, 33, 92


def center_geometry(win_w: int, win_h: int, screen_w: int, screen_h: int, left: int = 0, top: int = 0,
                    frame: tuple[int, int] = (0, 0)) -> tuple[int, int, int, int]:
    """Tamanho e posição (em pixels da tela) para abrir centralizado, cabendo na área livre.

    A área livre (sem a barra de tarefas) começa em left/top; frame é a moldura do Windows,
    que fica por fora de win_w/win_h.
    """
    w = min(win_w, screen_w - frame[0])
    h = min(win_h, screen_h - frame[1])
    return w, h, left + max((screen_w - w - frame[0]) // 2, 0), top + max((screen_h - h - frame[1]) // 2, 0)


def work_area() -> tuple[int, int, int, int]:
    """Área livre do monitor principal (sem a barra de tarefas): esquerda, topo, largura, altura."""
    rect = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def frame_size() -> tuple[int, int]:
    """Quanto a moldura do Windows soma à janela (largura, altura)."""
    metric = ctypes.windll.user32.GetSystemMetrics
    padding = metric(SM_CXPADDEDBORDER)
    return 2 * (metric(SM_CXSIZEFRAME) + padding), metric(SM_CYCAPTION) + 2 * (metric(SM_CYSIZEFRAME) + padding)


def app_size(win) -> tuple[int, int]:
    """Tamanho atual da janela no tamanho do app (o mesmo que center_on_screen recebe)."""
    scale = win._get_window_scaling()
    return round(win.winfo_width() / scale), round(win.winfo_height() / scale)


def center_on_screen(win, width: int | None = None, height: int | None = None) -> None:
    """width/height no tamanho do app (antes da escala do Windows); sem eles, usa o tamanho pedido pela janela."""
    win.update_idletasks()
    scale = win._get_window_scaling()
    w = round(width * scale) if width else win.winfo_reqwidth()
    h = round(height * scale) if height else win.winfo_reqheight()
    left, top, area_w, area_h = work_area()
    w, h, x, y = center_geometry(w, h, area_w, area_h, left, top, frame_size())
    # usa o tk direto (pixels reais): o geometry() do CustomTkinter multiplica pela escala
    tkinter.Wm.wm_geometry(win, f"{w}x{h}+{x}+{y}")
