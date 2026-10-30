"""Janela principal do ColouBaixô: prévia, fila de downloads e pasta de destino."""

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
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from ytdl.config import Config, load_config, save_config
from ytdl.downloader import Job, cleanup_stale_temp, fetch_info, fetch_oembed
from ytdl.errors import BOT_BLOCK, INVALID_LINK, NO_NODE_WARNING, Cancelled, DownloadError, FriendlyError
from ytdl.formats import VideoInfo, available_heights, format_duration, plan_video, quality_label, quality_options
from ytdl.paths import app_data_dir, resource_dir
from ytdl.playlist import PlaylistEntry, thumb_url
from ytdl.playlist_window import PlaylistWindow, ask_playlist
from ytdl.queue_model import Kind, QueueModel, Status
from ytdl.queue_view import ROW_THUMB, QueueView
from ytdl.settings import SettingsWindow
from ytdl.tools import Tools, load_tools, update_ytdlp
from ytdl.urls import canonical_url, extract_playlist_id, extract_video_id, extract_video_ids, should_autofill

log = logging.getLogger("ytdl")

APP_TITLE = "ColouBaixô"
BEST = "Melhor disponível"
THUMB_SIZE = (160, 90)
DEBOUNCE_MS = 400
POLL_MS = 100
RED = ("#d93025", "#d93025")
RED_HOVER = ("#b3261e", "#b3261e")
BLUE = ("#1a73e8", "#1a73e8")
BLUE_HOVER = ("#1558b0", "#1558b0")
GRAY = ("gray75", "gray30")
GRAY_HOVER = ("gray65", "gray40")
ERROR_COLOR = ("#c5221f", "#f28b82")
MUTED = ("gray35", "gray65")
GENERIC_ERROR = FriendlyError("Não foi possível baixar este vídeo. Tente atualizar o programa.", True)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        icon = resource_dir() / "assets" / "icon.ico"
        if icon.exists():
            self.after(250, lambda: self.iconbitmap(str(icon)))  # o CTk troca o ícone ao abrir
        self.geometry("760x660")
        self.minsize(640, 540)

        self.events: queue.Queue = queue.Queue()
        self.settings = load_config()
        self.tools: Tools | None = None
        self.info: VideoInfo | None = None
        self.url: str | None = None  # link canônico do vídeo em prévia
        self.quality_map: dict[str, int | None] = {}
        self.model = QueueModel()
        self.default_kind: Kind = "video"
        self.job: Job | None = None
        self.job_item: int | None = None
        self.paused = False
        self.worker: threading.Thread | None = None
        self.last_file: Path | None = None
        self._debounce_id = None
        self._preview_token = 0
        self._last_clip: str | None = None
        self._thumb = None  # mantém a referência da imagem viva
        self._settings_window: SettingsWindow | None = None
        self._asked_playlist: str | None = None
        self._detail_requests: queue.Queue = queue.Queue()
        self._thumb_requests: queue.Queue = queue.Queue()

        self._build()
        self._set_buttons(False)
        self._render_queue()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<FocusIn>", lambda e: self._autofill())
        self.after(POLL_MS, self._poll)
        self._status("Preparando componentes…")
        self._background(self._prepare_tools)
        self._background(self._thumb_worker)

    # --- montagem da tela ---------------------------------------------

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        pad = {"padx": 16}

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(16, 4), **pad)
        top.grid_columnconfigure(0, weight=1)
        self.entry = ctk.CTkEntry(top, placeholder_text="Cole um ou vários links do YouTube aqui…", height=36)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<KeyRelease>", lambda e: self._schedule_check())
        self.entry.bind("<<Paste>>", self._on_paste)
        ctk.CTkButton(top, text="⚙", width=36, height=36, font=ctk.CTkFont(size=20),
                      command=self.open_settings).grid(row=0, column=1, padx=(8, 0))

        folder = ctk.CTkFrame(self, fg_color="transparent")
        folder.grid(row=1, column=0, sticky="ew", pady=(0, 4), **pad)
        folder.grid_columnconfigure(0, weight=1)
        self.folder_label = ctk.CTkLabel(folder, text="", anchor="w", text_color=MUTED)
        self.folder_label.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(folder, text="Alterar", width=70, height=24, fg_color=GRAY, text_color=("gray10", "gray90"),
                      hover_color=GRAY_HOVER, command=self._choose_folder).grid(row=0, column=1)
        self._show_folder()

        self.preview = ctk.CTkFrame(self)
        self.preview.grid(row=2, column=0, sticky="ew", pady=4, **pad)
        self.preview.grid_columnconfigure(1, weight=1)
        self.thumb_label = ctk.CTkLabel(self.preview, text="", width=THUMB_SIZE[0], height=THUMB_SIZE[1])
        self.thumb_label.grid(row=0, column=0, rowspan=3, padx=12, pady=12)
        self.title_label = ctk.CTkLabel(self.preview, text="", font=ctk.CTkFont(size=15, weight="bold"),
                                        anchor="w", justify="left", wraplength=480)
        self.title_label.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(12, 0))
        self.meta_label = ctk.CTkLabel(self.preview, text="", anchor="w", text_color=MUTED)
        self.meta_label.grid(row=1, column=1, sticky="ew", padx=(0, 12))
        self.quality_menu = ctk.CTkOptionMenu(self.preview, values=[BEST], width=240)
        self.quality_menu.grid(row=2, column=1, sticky="w", padx=(0, 12), pady=(4, 12))
        self.preview.grid_remove()

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=3, column=0, sticky="w", pady=4, **pad)
        self.mp4_btn = ctk.CTkButton(buttons, text="⬇ MP4", width=110, height=36, fg_color=RED,
                                     hover_color=RED_HOVER, command=lambda: self._add_preview("video"))
        self.mp3_btn = ctk.CTkButton(buttons, text="♪ MP3", width=110, height=36, fg_color=BLUE,
                                     hover_color=BLUE_HOVER, command=lambda: self._add_preview("audio"))
        self.folder_btn = ctk.CTkButton(buttons, text="📁 Abrir pasta", width=130, height=36, fg_color=GRAY,
                                        text_color=("gray10", "gray90"), hover_color=GRAY_HOVER,
                                        command=self._open_folder)
        self.update_btn = ctk.CTkButton(buttons, text="Atualizar agora", width=130, height=36,
                                        command=self._update_engine)
        for i, b in enumerate((self.mp4_btn, self.mp3_btn, self.folder_btn)):
            b.grid(row=0, column=i, padx=(0, 8))

        self.status_label = ctk.CTkLabel(self, text="", anchor="w", justify="left", wraplength=720)
        self.status_label.grid(row=4, column=0, sticky="ew", **pad)
        self._normal_text_color = self.status_label.cget("text_color")

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=5, column=0, sticky="ew", pady=(8, 2), **pad)
        header.grid_columnconfigure(0, weight=1)
        self.queue_title = ctk.CTkLabel(header, text="Fila", anchor="w", font=ctk.CTkFont(weight="bold"))
        self.queue_title.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Formato para os próximos:", text_color=MUTED).grid(row=0, column=1, padx=(0, 6))
        self.kind_switch = ctk.CTkSegmentedButton(header, values=["MP4", "MP3"], command=self._on_default_kind)
        self.kind_switch.set("MP4")
        self.kind_switch.grid(row=0, column=2)

        self.queue_view = QueueView(self, on_toggle=self._on_toggle, on_kind=self._on_item_kind,
                                    on_remove=self._on_remove, on_open=self._on_open_item)
        self.queue_view.grid(row=6, column=0, sticky="nsew", **pad)
        self.grid_rowconfigure(6, weight=1)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=7, column=0, sticky="ew", pady=(6, 14), **pad)
        self.release_btn = ctk.CTkButton(actions, text="Baixar selecionados", height=32, command=self._release)
        self.cancel_all_btn = ctk.CTkButton(actions, text="Cancelar tudo", width=110, height=32, fg_color=GRAY,
                                            text_color=("gray10", "gray90"), hover_color=GRAY_HOVER,
                                            command=self._cancel_all)
        self.clear_btn = ctk.CTkButton(actions, text="Limpar finalizados", width=130, height=32, fg_color=GRAY,
                                       text_color=("gray10", "gray90"), hover_color=GRAY_HOVER,
                                       command=self._clear_finished)
        self.resume_btn = ctk.CTkButton(actions, text="▶ Continuar fila", width=130, height=32, command=self._resume)
        self.cancel_all_btn.grid(row=0, column=1, padx=(0, 8))
        self.clear_btn.grid(row=0, column=2)

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
    def fast(self) -> bool:
        """Computador sem aceleração de vídeo: evita conversões lentas."""
        return bool(self.tools) and self.tools.hw_encoder is None

    def _show_folder(self) -> None:
        self.folder_label.configure(text=f"📁 Salvando em: {self.settings.base_dir}")

    def _background(self, fn, *args) -> None:
        threading.Thread(target=fn, args=args, daemon=True).start()

    def _poll(self) -> None:
        try:
            drain_events(self.events, lambda kind, payload: getattr(self, f"_on_{kind}")(payload))
        finally:
            self.after(POLL_MS, self._poll)

    def report_callback_exception(self, exc, val, tb) -> None:
        # no .exe (--windowed) não há stderr: registra no log em vez de sumir
        log.error("erro na interface", exc_info=(exc, val, tb))

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
        self._status("" if tools.js_runtime else NO_NODE_WARNING)
        self._background(self._silent_update)
        self._background(self._detail_worker)
        self._autofill()
        self._check_entry()
        self.pump_queue()

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
        if should_autofill(clip, self.entry.get(), busy=False):
            self.entry.delete(0, "end")
            self.entry.insert(0, clip.strip())
            self._check_entry()

    def _on_paste(self, _event=None):
        try:
            clip = self.clipboard_get()
        except tkinter.TclError:
            return None
        if len(extract_video_ids(clip)) >= 2:
            self._add_many(clip)
            return "break"
        self._schedule_check()
        return None

    def _schedule_check(self) -> None:
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(DEBOUNCE_MS, self._check_entry)

    def _check_entry(self) -> None:
        self._debounce_id = None
        if not self.tools:
            return
        text = self.entry.get().strip()
        if len(extract_video_ids(text)) >= 2:
            self.entry.delete(0, "end")
            self._add_many(text)
            return
        video_id = extract_video_id(text)
        playlist_id = extract_playlist_id(text)
        if playlist_id and text != self._asked_playlist:
            self._asked_playlist = text  # pergunta uma vez por link
            if video_id is None or ask_playlist(self) == "playlist":
                self._open_playlist(text, playlist_id, video_id)
                if video_id is None:
                    return
        if not text:
            self._clear_preview()
            self._status("")
        elif video_id is None and playlist_id:
            return
        elif video_id is None:
            self._clear_preview()
            self._status(INVALID_LINK.message, True)
        elif canonical_url(video_id) != self.url:
            self._load_preview(canonical_url(video_id))

    def _open_playlist(self, url: str, playlist_id: str, preselect: str | None) -> None:
        PlaylistWindow(self, self.tools, url, playlist_id, preselect, self.default_kind, self._add_playlist)

    def _add_playlist(self, entries: list[PlaylistEntry], kind: Kind) -> None:
        added, duplicates = self.add_to_queue(
            [(e.video_id, {"title": e.title, "channel": e.channel, "duration": e.duration}) for e in entries],
            kind, Status.QUEUED)
        message = f"{added} vídeos adicionados à fila."
        if duplicates:
            message += f" ({duplicates} já estavam na fila)"
        self._status(message)
        self.pump_queue()

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
                image = _download_image(info.thumbnail_url, THUMB_SIZE)
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
        self.quality_map = quality_options(info, fast=self.fast)
        top = quality_label(available_heights(info)[0])
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
        self._status("" if self.tools.js_runtime else NO_NODE_WARNING)

    def _on_preview_failed(self, payload) -> None:
        token, friendly = payload
        if token != self._preview_token:
            return
        self.url = None
        self._status(friendly.message, True)
        self._show_update_button(friendly.suggest_update)

    # --- fila: entrada de itens -----------------------------------------

    def add_to_queue(self, entries: list[tuple[str, dict]], kind: Kind, status: Status) -> tuple[int, int]:
        """Adiciona itens; devolve (adicionados, repetidos)."""
        added = duplicates = 0
        for video_id, fields in entries:
            item = self.model.add(video_id, kind, status, **fields)
            if item is None:
                duplicates += 1
                continue
            added += 1
            self._thumb_requests.put(video_id)
            if item.title is None:
                self._detail_requests.put((item.id, video_id))
        self._render_queue()
        return added, duplicates

    def _add_preview(self, kind: Kind) -> None:
        if not self.info:
            return
        info = self.info
        res = self.quality_map.get(self.quality_menu.get()) if kind == "video" else None
        added, _ = self.add_to_queue(
            [(info.id, {"title": info.title, "channel": info.channel, "duration": info.duration,
                        "info": info, "res": res})], kind, Status.QUEUED)
        self._show_update_button(False)
        self._status(f"Adicionado à fila: {info.title}" if added else "Já está na fila.")
        self.pump_queue()

    def _add_many(self, text: str) -> None:
        ids = extract_video_ids(text)
        pieces = [p for p in text.split() if "youtu" in p.lower() or "://" in p]
        unrecognized = sum(1 for p in pieces if extract_video_id(p) is None)
        added, duplicates = self.add_to_queue([(v, {}) for v in ids], self.default_kind, Status.REVIEW)
        message = f"{added} links adicionados para revisão: desmarque o que não quiser e clique em Baixar selecionados."
        if duplicates:
            message += f" ({duplicates} já estavam na fila)"
        if unrecognized:
            message += f" {unrecognized} links não reconhecidos."
        self._status(message)

    # --- fila: ações do usuário -------------------------------------------

    def _on_default_kind(self, label: str) -> None:
        self.default_kind = "audio" if label == "MP3" else "video"

    def _on_toggle(self, item_id: int, checked: bool) -> None:
        self.model.set_checked(item_id, checked)
        self._render_queue()

    def _on_item_kind(self, item_id: int, kind: Kind) -> None:
        if not self.model.set_kind(item_id, kind):
            self._status("Este vídeo já está na fila nesse formato.", True)
        self._render_queue()

    def _on_remove(self, item_id: int) -> None:
        item = self.model.remove(item_id)
        if item and item.status == Status.DOWNLOADING and self.job:
            self.job.cancel()
        self._render_queue()

    def _on_open_item(self, item_id: int) -> None:
        item = self.model.get(item_id)
        if item and item.status == Status.DONE and item.path and item.path.exists():
            subprocess.Popen(f'explorer /select,"{item.path}"')

    def _release(self) -> None:
        self.model.release_checked()
        self._render_queue()
        self.pump_queue()

    def _cancel_all(self) -> None:
        current = self.model.cancel_all()
        if current and self.job:
            self.job.cancel()
        self._render_queue()

    def _clear_finished(self) -> None:
        self.model.clear_finished()
        self._render_queue()

    def _render_queue(self) -> None:
        self.queue_view.render(self.model.items)
        self.queue_title.configure(text=f"Fila ({len(self.model.items)})")
        pending = self.model.review_checked_count()
        if pending:
            self.release_btn.configure(text=f"Baixar selecionados ({pending})")
            self.release_btn.grid(row=0, column=0, padx=(0, 8))
        else:
            self.release_btn.grid_remove()
        if self.paused:
            self.resume_btn.grid(row=0, column=3, padx=(8, 0))
        else:
            self.resume_btn.grid_remove()

    # --- fila: execução ---------------------------------------------------

    def _resume(self) -> None:
        self.paused = False
        self._status("Continuando a fila…")
        self._render_queue()
        self.pump_queue()

    def pump_queue(self) -> None:
        if self.job or not self.tools or self.paused:
            return
        item = self.model.next_item()
        if item is None:
            return
        self.model.start(item.id)
        item_id, video_id, kind, info, res = item.id, item.video_id, item.kind, item.info, item.res
        base = self.settings.base_dir  # a pasta vale a partir do início de cada item
        self.job_item = item_id
        self.job = job = Job(self.tools, app_data_dir() / "tmp",
                             lambda p: self.events.put(("q_progress", (item_id, p))))
        tools, fast = self.tools, self.fast
        self._render_queue()

        def work(info=info):
            url = canonical_url(video_id)
            try:
                if info is None:
                    info = fetch_info(tools, url)
                    self.events.put(("q_info", (item_id, info)))
                if kind == "video":
                    path = job.run_video(url, info, plan_video(info, res, fast=fast), base)
                else:
                    path = job.run_audio(url, info, base)
                self.events.put(("q_done", (item_id, path)))
            except Cancelled:
                self.events.put(("q_cancelled", item_id))
            except DownloadError as exc:
                self.events.put(("q_failed", (item_id, exc.friendly)))
            except Exception:
                log.exception("falha inesperada no download")
                self.events.put(("q_failed", (item_id, GENERIC_ERROR)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _job_finished(self, item_id: int) -> None:
        if self.job_item == item_id:
            self.job = self.job_item = self.worker = None
        self._render_queue()
        self.pump_queue()

    def _on_q_progress(self, payload) -> None:
        item_id, progress = payload
        item = self.model.get(item_id)
        if item and item.status == Status.DOWNLOADING:
            item.progress = progress
            self.queue_view.update_item(item)

    def _on_q_info(self, payload) -> None:
        item_id, info = payload
        if item := self.model.get(item_id):
            item.info, item.title, item.channel, item.duration = info, info.title, info.channel, info.duration
            self.queue_view.update_item(item)

    def _on_q_done(self, payload) -> None:
        item_id, path = payload
        self.model.finish(item_id, path)
        self.last_file = path
        self._job_finished(item_id)

    def _on_q_failed(self, payload) -> None:
        item_id, friendly = payload
        if friendly == BOT_BLOCK:
            # bloqueio vale para todos os vídeos: pausa em vez de marcar a fila inteira como erro
            self.model.requeue(item_id)
            self.paused = True
            self._status("O YouTube bloqueou temporariamente os downloads desta internet. "
                         "A fila foi pausada; tente continuar daqui a algum tempo.", True)
        else:
            self.model.fail(item_id, friendly.message)
            self._show_update_button(friendly.suggest_update)
        self._job_finished(item_id)

    def _on_q_cancelled(self, item_id: int) -> None:
        self.model.mark_cancelled(item_id)
        self._job_finished(item_id)

    # --- trabalhadores em segundo plano -----------------------------------

    def _detail_worker(self) -> None:
        """Busca título/canal dos itens colados, um por vez."""
        while True:
            item_id, video_id = self._detail_requests.get()
            try:
                # consulta leve primeiro: poupa extrações do yt-dlp (o YouTube bloqueia excesso)
                basic = fetch_oembed(video_id)
                if basic:
                    self.events.put(("q_basic", (item_id, basic)))
                    continue
                info = fetch_info(self.tools, canonical_url(video_id))
                self.events.put(("q_info", (item_id, info)))
            except DownloadError as exc:
                self.events.put(("q_info_failed", (item_id, exc.friendly.message)))
            except Exception:
                log.exception("falha ao buscar detalhes")
                self.events.put(("q_info_failed", (item_id, GENERIC_ERROR.message)))

    def _on_q_basic(self, payload) -> None:
        item_id, (title, channel) = payload
        if item := self.model.get(item_id):
            item.title, item.channel = title, channel
            self.queue_view.update_item(item)

    def _on_q_info_failed(self, payload) -> None:
        item_id, message = payload
        item = self.model.get(item_id)
        if item and item.status in (Status.REVIEW, Status.QUEUED):
            self.model.fail(item_id, message)
            self._render_queue()

    def _thumb_worker(self) -> None:
        seen: set[str] = set()
        while True:
            video_id = self._thumb_requests.get()
            if video_id in seen:
                continue
            seen.add(video_id)
            image = _download_image(thumb_url(video_id), ROW_THUMB)
            if image:
                self.events.put(("thumb", (video_id, image)))

    def _on_thumb(self, payload) -> None:
        video_id, image = payload
        self.queue_view.set_thumb(video_id, ctk.CTkImage(light_image=image, dark_image=image, size=ROW_THUMB))

    # --- pasta e configurações ----------------------------------------

    def _choose_folder(self) -> None:
        chosen = filedialog.askdirectory(parent=self, initialdir=self.settings.base_dir,
                                         title="Escolha a pasta onde salvar")
        if chosen:
            config = Config(base_dir=Path(chosen))
            save_config(config)
            self._on_settings_saved(config)

    def _open_folder(self) -> None:
        if self.last_file and self.last_file.exists():
            subprocess.Popen(f'explorer /select,"{self.last_file}"')
            return
        base = self.settings.base_dir
        base.mkdir(parents=True, exist_ok=True)
        os.startfile(base)

    def open_settings(self) -> None:
        if self._settings_window and self._settings_window.winfo_exists():
            self._settings_window.focus()
            return
        self._settings_window = SettingsWindow(self, self.tools, self.settings, self._on_settings_saved)

    def _on_settings_saved(self, config: Config) -> None:
        self.settings = config
        self.last_file = None
        self._show_folder()

    def _on_close(self) -> None:
        if self.job:
            if not messagebox.askyesno(APP_TITLE, "Há downloads em andamento. Fechar e cancelar?", parent=self):
                return
            self.job.cancel()
            if self.worker:
                self.worker.join(timeout=5)
        self.destroy()


def drain_events(q: queue.Queue, handle) -> None:
    """Processa todos os eventos pendentes; um handler com erro não derruba os demais."""
    while True:
        try:
            kind, payload = q.get_nowait()
        except queue.Empty:
            return
        try:
            handle(kind, payload)
        except Exception:
            log.exception("erro ao tratar o evento %s", kind)


def _download_image(url: str | None, size: tuple[int, int]) -> Image.Image | None:
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            image = Image.open(io.BytesIO(resp.read())).convert("RGB")
        return image.resize(size, Image.LANCZOS)
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
