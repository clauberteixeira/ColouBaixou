"""Janela principal do YouTube Downloader (modelo B: com prévia)."""

import io
import logging
import os
import queue
import subprocess
import threading
import tkinter
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from ytdl.config import load_config
from ytdl.downloader import Job, cleanup_stale_temp, fetch_info
from ytdl.errors import INVALID_LINK, NO_NODE_WARNING, Cancelled, DownloadError, FriendlyError
from ytdl.formats import VideoInfo, available_heights, format_duration, plan_video, quality_label
from ytdl.paths import app_data_dir
from ytdl.progress import Progress, describe
from ytdl.tools import Tools, load_tools, update_ytdlp
from ytdl.urls import canonical_url, extract_video_id, should_autofill

log = logging.getLogger("ytdl")

BEST = "Melhor disponível"
THUMB_SIZE = (160, 90)
DEBOUNCE_MS = 400
POLL_MS = 100
RED = ("#d93025", "#d93025")
RED_HOVER = ("#b3261e", "#b3261e")
BLUE = ("#1a73e8", "#1a73e8")
BLUE_HOVER = ("#1558b0", "#1558b0")
ERROR_COLOR = ("#c5221f", "#f28b82")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("680x400")
        self.minsize(560, 360)

        self.events: queue.Queue = queue.Queue()
        self.settings = load_config()
        self.tools: Tools | None = None
        self.info: VideoInfo | None = None
        self.url: str | None = None  # link canônico do vídeo em prévia
        self.quality_map: dict[str, int | None] = {}
        self.job: Job | None = None
        self.worker: threading.Thread | None = None
        self.last_file: Path | None = None
        self._debounce_id = None
        self._preview_token = 0
        self._last_clip: str | None = None
        self._thumb = None  # mantém a referência da imagem viva

        self._build()
        self._set_buttons(False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<FocusIn>", lambda e: self._autofill())
        self.after(POLL_MS, self._poll)
        self._status("Preparando componentes…")
        self._background(self._prepare_tools)

    # --- montagem da tela ---------------------------------------------

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        pad = {"padx": 16}

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(16, 8), **pad)
        top.grid_columnconfigure(0, weight=1)
        self.entry = ctk.CTkEntry(top, placeholder_text="Cole o link do YouTube aqui…", height=36)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<KeyRelease>", lambda e: self._schedule_check())
        self.entry.bind("<<Paste>>", lambda e: self._schedule_check())
        ctk.CTkButton(top, text="⚙", width=36, height=36, font=ctk.CTkFont(size=20),
                      command=self.open_settings).grid(row=0, column=1, padx=(8, 0))

        self.preview = ctk.CTkFrame(self)
        self.preview.grid(row=1, column=0, sticky="ew", pady=8, **pad)
        self.preview.grid_columnconfigure(1, weight=1)
        self.thumb_label = ctk.CTkLabel(self.preview, text="", width=THUMB_SIZE[0], height=THUMB_SIZE[1])
        self.thumb_label.grid(row=0, column=0, rowspan=3, padx=12, pady=12)
        self.title_label = ctk.CTkLabel(self.preview, text="", font=ctk.CTkFont(size=15, weight="bold"),
                                        anchor="w", justify="left", wraplength=420)
        self.title_label.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(12, 0))
        self.meta_label = ctk.CTkLabel(self.preview, text="", anchor="w", text_color=("gray35", "gray65"))
        self.meta_label.grid(row=1, column=1, sticky="ew", padx=(0, 12))
        self.quality_menu = ctk.CTkOptionMenu(self.preview, values=[BEST], width=220)
        self.quality_menu.grid(row=2, column=1, sticky="w", padx=(0, 12), pady=(4, 12))
        self.preview.grid_remove()

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="w", pady=8, **pad)
        self.mp4_btn = ctk.CTkButton(buttons, text="⬇ MP4", width=110, height=36, fg_color=RED,
                                     hover_color=RED_HOVER, command=lambda: self._start_download("video"))
        self.mp3_btn = ctk.CTkButton(buttons, text="♪ MP3", width=110, height=36, fg_color=BLUE,
                                     hover_color=BLUE_HOVER, command=lambda: self._start_download("audio"))
        self.folder_btn = ctk.CTkButton(buttons, text="📁 Abrir pasta", width=130, height=36,
                                        fg_color=("gray75", "gray30"), text_color=("gray10", "gray90"),
                                        hover_color=("gray65", "gray40"), command=self._open_folder)
        self.cancel_btn = ctk.CTkButton(buttons, text="Cancelar", width=100, height=36,
                                        fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
                                        command=self._cancel)
        self.update_btn = ctk.CTkButton(buttons, text="Atualizar agora", width=130, height=36,
                                        command=self._update_engine)
        for i, b in enumerate((self.mp4_btn, self.mp3_btn, self.folder_btn)):
            b.grid(row=0, column=i, padx=(0, 8))

        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=3, column=0, sticky="ew", pady=(8, 4), **pad)
        self.progress.set(0)
        self.progress.grid_remove()
        self.status_label = ctk.CTkLabel(self, text="", anchor="w", justify="left", wraplength=640)
        self.status_label.grid(row=4, column=0, sticky="ew", pady=(0, 16), **pad)
        self._normal_text_color = self.status_label.cget("text_color")

    # --- utilidades de tela -------------------------------------------

    def _status(self, text: str, error: bool = False) -> None:
        self.status_label.configure(text=text, text_color=ERROR_COLOR if error else self._normal_text_color)

    def _set_buttons(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.mp4_btn.configure(state=state)
        self.mp3_btn.configure(state=state)

    def _show_update_button(self, show: bool) -> None:
        if show:
            self.update_btn.grid(row=0, column=4, padx=(0, 8))
        else:
            self.update_btn.grid_remove()

    @property
    def busy(self) -> bool:
        return self.job is not None

    def _background(self, fn, *args) -> None:
        threading.Thread(target=fn, args=args, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                getattr(self, f"_on_{kind}")(payload)
        except queue.Empty:
            pass
        self.after(POLL_MS, self._poll)

    # --- componentes --------------------------------------------------

    def _prepare_tools(self) -> None:
        try:
            cleanup_stale_temp(app_data_dir() / "tmp")
            self.events.put(("tools_ready", load_tools()))
        except Exception as exc:  # sem internet na primeira vez, ffmpeg ausente…
            log.exception("falha ao preparar ferramentas")
            self.events.put(("tools_failed", str(exc)))

    def _on_tools_ready(self, tools: Tools) -> None:
        self.tools = tools
        self._status(NO_NODE_WARNING if tools.node is None else "")
        self._background(self._silent_update)
        self._autofill()
        self._check_entry()

    def _on_tools_failed(self, message: str) -> None:
        self._status("Não foi possível preparar os componentes. Verifique a internet e abra o programa de novo.", True)

    def _silent_update(self) -> None:
        try:
            update_ytdlp(self.tools.ytdlp)
        except Exception:
            log.info("atualização automática não foi possível agora")

    def _update_engine(self) -> None:
        if not self.tools:
            return
        self._show_update_button(False)
        self._status("Atualizando o motor de download…")

        def work():
            try:
                self.events.put(("updated", update_ytdlp(self.tools.ytdlp)))
            except Exception:
                self.events.put(("update_failed", None))

        self._background(work)

    def _on_updated(self, version: str) -> None:
        self._status(f"Motor de download atualizado ({version}). Tente de novo.")

    def _on_update_failed(self, _) -> None:
        self._status("Não foi possível atualizar agora. Tente mais tarde.", True)

    # --- link e prévia ------------------------------------------------

    def _autofill(self) -> None:
        if not self.tools:
            return
        try:
            clip = self.clipboard_get()
        except tkinter.TclError:
            return
        if clip == self._last_clip:
            return
        self._last_clip = clip
        if should_autofill(clip, self.entry.get(), self.busy):
            self.entry.delete(0, "end")
            self.entry.insert(0, clip.strip())
            self._check_entry()

    def _schedule_check(self) -> None:
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(DEBOUNCE_MS, self._check_entry)

    def _check_entry(self) -> None:
        self._debounce_id = None
        if self.busy or not self.tools:
            return
        text = self.entry.get().strip()
        video_id = extract_video_id(text)
        if not text:
            self._clear_preview()
            self._status("")
        elif video_id is None:
            self._clear_preview()
            self._status(INVALID_LINK.message, True)
        elif canonical_url(video_id) != self.url:
            self._load_preview(canonical_url(video_id))

    def _clear_preview(self) -> None:
        self._preview_token += 1
        self.info = self.url = None
        self.preview.grid_remove()
        self._set_buttons(False)

    def _load_preview(self, url: str) -> None:
        self._clear_preview()
        self.url = url
        token = self._preview_token
        self._show_update_button(False)
        self._status("Carregando informações do vídeo…")

        def work():
            try:
                info = fetch_info(self.tools, url)
                image = _download_thumbnail(info.thumbnail_url)
                self.events.put(("preview", (token, info, image)))
            except DownloadError as exc:
                self.events.put(("preview_failed", (token, exc.friendly)))
            except Exception:
                log.exception("falha na prévia")
                self.events.put(("preview_failed", (token, FriendlyError(
                    "Não foi possível carregar este vídeo. Tente atualizar o programa.", True))))

        self._background(work)

    def _on_preview(self, payload) -> None:
        token, info, image = payload
        if token != self._preview_token:
            return
        self.info = info
        heights = available_heights(info)
        top = quality_label(heights[0])
        self.quality_map = {f"{BEST} ({top})": None}
        self.quality_map.update({quality_label(h): h for h in heights[1:]})
        labels = list(self.quality_map)
        self.quality_menu.configure(values=labels)
        self.quality_menu.set(labels[0])
        self.title_label.configure(text=info.title)
        self.meta_label.configure(text=f"{info.channel} · {format_duration(info.duration)} · até {top}")
        if image:
            self._thumb = ctk.CTkImage(light_image=image, dark_image=image, size=THUMB_SIZE)
            self.thumb_label.configure(image=self._thumb)
        else:
            self._thumb = None
            self.thumb_label.configure(image=None)
        self.preview.grid()
        self._set_buttons(True)
        self._status("" if self.tools.node else NO_NODE_WARNING)

    def _on_preview_failed(self, payload) -> None:
        token, friendly = payload
        if token != self._preview_token:
            return
        self.url = None
        self._status(friendly.message, True)
        self._show_update_button(friendly.suggest_update)

    # --- download -----------------------------------------------------

    def _start_download(self, kind: str) -> None:
        if self.busy or not self.info:
            return
        info, url = self.info, self.url
        base = self.settings.base_dir
        self.job = Job(self.tools, app_data_dir() / "tmp", lambda p: self.events.put(("progress", p)))
        job = self.job
        plan = plan_video(info, self.quality_map.get(self.quality_menu.get())) if kind == "video" else None

        self._set_buttons(False)
        self.entry.configure(state="disabled")
        self._show_update_button(False)
        self.cancel_btn.grid(row=0, column=3, padx=(0, 8))
        self.progress.grid()
        self._set_progress(0.0)
        self._status("Iniciando download…")

        def work():
            try:
                path = job.run_video(url, info, plan, base) if plan else job.run_audio(url, info, base)
                self.events.put(("done", path))
            except Cancelled:
                self.events.put(("cancelled", None))
            except DownloadError as exc:
                self.events.put(("failed", exc.friendly))
            except Exception:
                log.exception("falha inesperada no download")
                self.events.put(("failed", FriendlyError(
                    "Não foi possível baixar este vídeo. Tente atualizar o programa.", True)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _set_progress(self, fraction: float | None) -> None:
        if fraction is None:
            if self.progress.cget("mode") != "indeterminate":
                self.progress.configure(mode="indeterminate")
                self.progress.start()
            return
        if self.progress.cget("mode") != "determinate":
            self.progress.stop()
            self.progress.configure(mode="determinate")
        self.progress.set(fraction)

    def _on_progress(self, p: Progress) -> None:
        if not self.busy:
            return
        self._set_progress(None if p.percent is None else p.percent / 100)
        self._status(describe(p))

    def _finish(self) -> None:
        self.job = None
        self.worker = None
        self.cancel_btn.grid_remove()
        self._set_progress(0.0)
        self.progress.grid_remove()
        self.entry.configure(state="normal")
        self._set_buttons(self.info is not None)

    def _on_done(self, path: Path) -> None:
        self._finish()
        self.last_file = path
        self._status(f"Concluído: {path}")

    def _on_failed(self, friendly: FriendlyError) -> None:
        self._finish()
        self._status(friendly.message, True)
        self._show_update_button(friendly.suggest_update)

    def _on_cancelled(self, _) -> None:
        self._finish()
        self._status("Download cancelado.")

    def _cancel(self) -> None:
        if self.job:
            self._status("Cancelando…")
            self.job.cancel()

    # --- pasta e configurações ----------------------------------------

    def _open_folder(self) -> None:
        if self.last_file and self.last_file.exists():
            subprocess.Popen(f'explorer /select,"{self.last_file}"')
            return
        base = self.settings.base_dir
        base.mkdir(parents=True, exist_ok=True)
        os.startfile(base)

    def open_settings(self) -> None:
        """Abre a janela de Configurações (Task 9)."""

    def _on_close(self) -> None:
        if self.job:
            self.job.cancel()
            if self.worker:
                self.worker.join(timeout=5)
        self.destroy()


def _download_thumbnail(url: str | None) -> Image.Image | None:
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            image = Image.open(io.BytesIO(resp.read())).convert("RGB")
        return image.resize(THUMB_SIZE, Image.LANCZOS)
    except Exception:
        log.warning("miniatura indisponível: %s", url)
        return None


def _setup_logging() -> None:
    folder = app_data_dir() / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(folder / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


def main() -> None:
    _setup_logging()
    ctk.set_appearance_mode("system")
    App().mainloop()
