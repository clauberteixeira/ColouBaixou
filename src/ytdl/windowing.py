"""Abrir janelas centralizadas na tela (cabendo em telas pequenas)."""

import tkinter

SCREEN_FIT = 0.92  # sobra espaço para a barra de tarefas


def center_geometry(win_w: int, win_h: int, screen_w: int, screen_h: int) -> tuple[int, int, int, int]:
    """Tamanho e posição (em pixels da tela) para abrir centralizado, cabendo em telas pequenas."""
    w = min(win_w, int(screen_w * SCREEN_FIT))
    h = min(win_h, int(screen_h * SCREEN_FIT))
    return w, h, max((screen_w - w) // 2, 0), max((screen_h - h) // 2, 0)


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
    w, h, x, y = center_geometry(w, h, win.winfo_screenwidth(), win.winfo_screenheight())
    # usa o tk direto (pixels reais): o geometry() do CustomTkinter multiplica pela escala
    tkinter.Wm.wm_geometry(win, f"{w}x{h}+{x}+{y}")
