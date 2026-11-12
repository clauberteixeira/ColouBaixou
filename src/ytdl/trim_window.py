"""Janela "Escolher trecho": assiste ao vídeo e marca início e fim arrastando a linha do tempo."""

import queue
import subprocess
import threading
import time
import tkinter
import winsound
from pathlib import Path
from typing import Callable

import customtkinter as ctk
from PIL import Image, ImageTk

from ytdl.clip import Clip, as_clip, check_range, join_hms, split_hms
from ytdl.downloader import Job
from ytdl.errors import Cancelled, DownloadError
from ytdl.formats import VideoInfo, format_duration
from ytdl.paths import resource_dir
from ytdl.preview import (FPS, FRAME, FRAME_BYTES, MAX_PREVIEW_S, due_frame, frame_args, frames_args,
                          play_length, sound_args)
from ytdl.queue_model import Kind
from ytdl.timeline import Timeline
from ytdl.tools import NO_WINDOW, Tools
from ytdl.windowing import center_on_screen

TICK_MS = 30
GRAB_DELAY_MS = 40  # ao arrastar, espera a mão parar um instante antes de buscar a imagem
MUTED = ("gray35", "gray65")
TEXT = ("gray10", "gray90")
ERROR_COLOR = ("#c5221f", "#f28b82")
RED, RED_HOVER = ("#d93025", "#d93025"), ("#b3261e", "#b3261e")
BLUE, BLUE_HOVER = ("#1a73e8", "#1a73e8"), ("#1558b0", "#1558b0")


def play_wav(path: Path) -> None:
    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)


def stop_wav() -> None:
    winsound.PlaySound(None, 0)


class TrimWindow(ctk.CTkToplevel):
    def __init__(self, master, tools: Tools, info: VideoInfo, work_dir: Path, cache: dict[str, Path],
                 on_add: Callable[[Kind, Clip | None, VideoInfo], None],
                 play_sound: Callable[[Path], None] = play_wav, stop_sound: Callable[[], None] = stop_wav):
        super().__init__(master)
        self.title("Escolher trecho")
        icon = resource_dir() / "assets" / "icon.ico"
        if icon.exists():
            self.after(250, lambda: self.iconbitmap(str(icon)))  # o CTk troca o ícone ao abrir
        self.resizable(False, False)
        self.tools, self.info, self.cache, self.on_add = tools, info, cache, on_add
        self.play_sound, self.stop_sound = play_sound, stop_sound
        self.ffmpeg = tools.ffmpeg_dir / "ffmpeg.exe"
        self.dir = work_dir / info.id
        self.duration = max(info.duration, 1)
        self.start, self.end, self.playhead = 0, self.duration, 0.0
        self.file: Path | None = cache.get(info.id)
        self.events: queue.Queue = queue.Queue()
        self._frames: queue.Queue = queue.Queue(maxsize=FPS * 2)
        self._pending: tuple | None = None  # imagem que chegou antes da hora
        self._token = 0  # muda a cada ▶/⏸: o que for de uma reprodução antiga é descartado
        self._grab_seq = 0
        self._grab_after: str | None = None
        self._playing = False
        self._t0: float | None = None
        self._play_pos = self._play_len = 0.0
        self._proc: subprocess.Popen | None = None
        self._wav: Path | None = None
        self._job: Job | None = None
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.close)
        # atalhos só fora dos campos de tempo (lá as setas e o espaço servem para digitar)
        self.bind("<Left>", lambda e: self._typing() or self.timeline.nudge(-1))
        self.bind("<Right>", lambda e: self._typing() or self.timeline.nudge(1))
        self.bind("<space>", lambda e: self._typing() or self.toggle_play())
        center_on_screen(self)
        self.transient(master)
        self.after(TICK_MS, self._tick)
        if self.file:
            self._ready(self.file)
        elif info.duration > MAX_PREVIEW_S or not info.raw:
            self.note.configure(text="Vídeo com mais de 30 min: sem prévia de imagem e som.")
        else:
            self._download_preview()

    # --- tela ----------------------------------------------------------

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=self.info.title, font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
                     justify="left", wraplength=FRAME[0]).grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        self._photo = ImageTk.PhotoImage(Image.new("RGB", FRAME))
        self.screen = tkinter.Label(self, image=self._photo, bg="black", borderwidth=0)
        self.screen.grid(row=1, column=0, padx=16)

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 0))
        bar.grid_columnconfigure(2, weight=1)
        self.play_btn = ctk.CTkButton(bar, text="▶", width=44, height=32, state="disabled",
                                      font=ctk.CTkFont(size=16), command=self.toggle_play)
        self.play_btn.grid(row=0, column=0)
        self.clock = ctk.CTkLabel(bar, text="", font=ctk.CTkFont(family="Consolas", size=13))
        self.clock.grid(row=0, column=1, padx=10)
        self.note = ctk.CTkLabel(bar, text="", text_color=MUTED, anchor="e")
        self.note.grid(row=0, column=2, sticky="e")

        bg = self._apply_appearance_mode(self.cget("fg_color"))
        self.timeline = Timeline(self, self.duration, self._on_range, self._on_seek, bg=bg)
        self.timeline.grid(row=3, column=0, sticky="ew", padx=16, pady=(4, 0))
        fields = ctk.CTkFrame(self, fg_color="transparent")
        fields.grid(row=4, column=0, sticky="w", padx=16, pady=(6, 0))
        self.fields = {"start": self._time_fields(fields, "Início", "start", 0),
                       "end": self._time_fields(fields, "Fim", "end", 1)}
        self.range_label = ctk.CTkLabel(self, text="", anchor="w")
        self.range_label.grid(row=5, column=0, sticky="ew", padx=16, pady=(4, 0))
        ctk.CTkLabel(self, text="Arraste as alças azuis ou digite hora, minuto e segundo (Enter confirma). "
                                "Setas ← → ajustam 1 segundo; espaço toca/pausa.", text_color=MUTED, anchor="w",
                     justify="left", wraplength=FRAME[0]).grid(row=6, column=0, sticky="ew", padx=16)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=7, column=0, sticky="w", padx=16, pady=(12, 16))
        ctk.CTkButton(buttons, text="⬇ Baixar trecho em MP4", height=36, fg_color=RED, hover_color=RED_HOVER,
                      command=lambda: self._add("video")).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(buttons, text="♪ Baixar trecho em MP3", height=36, fg_color=BLUE, hover_color=BLUE_HOVER,
                      command=lambda: self._add("audio")).grid(row=0, column=1)
        self._show_times()

    def _time_fields(self, master, label: str, which: str, column: int) -> tuple[ctk.CTkEntry, ...]:
        """Grupo "Início [h]:[mm]:[ss]"; Enter ou sair do campo aplica na linha do tempo."""
        group = ctk.CTkFrame(master, fg_color="transparent")
        group.grid(row=0, column=column, padx=(0, 28))
        ctk.CTkLabel(group, text=label).grid(row=0, column=0, padx=(0, 8))
        entries = []
        for i, hint in enumerate(("hora", "min", "seg")):
            if i:
                ctk.CTkLabel(group, text=":").grid(row=0, column=2 * i, padx=2)
            entry = ctk.CTkEntry(group, width=42, justify="center")
            entry.grid(row=0, column=2 * i + 1)
            ctk.CTkLabel(group, text=hint, text_color=MUTED, font=ctk.CTkFont(size=10)).grid(
                row=1, column=2 * i + 1)
            entry.bind("<Return>", lambda e: self._typed(which))
            entry.bind("<FocusOut>", lambda e: self.after_idle(self._left_fields, which))
            entries.append(entry)
        return tuple(entries)

    def _left_fields(self, which: str) -> None:
        """Só aplica ao sair do grupo: indo da hora para o minuto, o tempo ainda está pela metade."""
        try:
            focus = self.focus_get()
        except (KeyError, tkinter.TclError):  # foco num menu ou em outra janela
            focus = None
        if not any(focus is entry._entry for entry in self.fields[which]):
            self._typed(which)

    def _typed(self, which: str) -> None:
        t = join_hms(*(e.get() for e in self.fields[which]))
        if t is not None:
            self.timeline.active = which
            self.timeline.move(which, t)  # ajusta aos limites e avisa _on_range
        self._show_times(force=which)  # número inválido ou fora do vídeo: os campos voltam ao valor certo

    def _show_times(self, force: str | None = None) -> None:
        self.clock.configure(text=f"{format_duration(int(self.playhead))} / {format_duration(self.duration)}")
        self.range_label.configure(text=f"Trecho de {format_duration(self.end - self.start)}", text_color=TEXT)
        for which, value in (("start", self.start), ("end", self.end)):
            for entry, number in zip(self.fields[which], split_hms(value)):
                text = f"{number:02d}" if entry is not self.fields[which][0] else str(number)
                if entry.get() != text and (force == which or entry is not self.focus_get()):  # não atrapalha quem digita
                    entry.delete(0, "end")
                    entry.insert(0, text)

    def _typing(self) -> bool:
        return isinstance(self.focus_get(), tkinter.Entry)

    def _show(self, data: bytes) -> None:
        self._photo.paste(Image.frombuffer("RGB", FRAME, data, "raw", "RGB", 0, 1))

    def _background(self, fn, *args) -> None:
        threading.Thread(target=fn, args=args, daemon=True).start()

    # --- cópia leve para assistir ------------------------------------

    def _download_preview(self) -> None:
        self.note.configure(text="Preparando a prévia…")
        self._job = Job(self.tools, self.dir, lambda p: self.events.put(("progress", p.percent)))
        job = self._job

        def work():
            try:
                self.events.put(("ready", job.run_preview(self.info, self.dir)))
            except Cancelled:
                pass
            except DownloadError as exc:
                self.events.put(("failed", exc.friendly.message))
            except Exception:
                self.events.put(("failed", "Não foi possível preparar a prévia."))

        self._background(work)

    def _ready(self, path: Path) -> None:
        self.file = self.cache[self.info.id] = path
        self.play_btn.configure(state="normal")
        self.note.configure(text="")
        self._grab(0)

    # --- imagem parada (ao arrastar ou clicar) -------------------------

    def _grab(self, t: float) -> None:
        if not self.file:
            return
        if self._grab_after:
            self.after_cancel(self._grab_after)
        self._grab_after = self.after(GRAB_DELAY_MS, self._grab_now, t)

    def _grab_now(self, t: float) -> None:
        self._grab_after = None
        self._grab_seq += 1
        seq, args = self._grab_seq, frame_args(self.ffmpeg, self.file, min(t, self.duration - 0.5))

        def work():
            result = subprocess.run(args, capture_output=True, creationflags=NO_WINDOW)
            if len(result.stdout) == FRAME_BYTES:
                self.events.put(("frame", (seq, result.stdout)))

        self._background(work)

    # --- linha do tempo -------------------------------------------------

    def _on_range(self, start: int, end: int, which: str) -> None:
        self.stop()
        self.start, self.end = start, end
        self.playhead = start  # o ▶ toca o trecho desde o começo
        self.timeline.set_playhead(start)
        self._show_times()
        self._grab(start if which == "start" else max(end - 1, start))  # mostra onde a alça está

    def _on_seek(self, t: float) -> None:
        was_playing = self._playing
        self.stop()
        self.playhead = t
        self.timeline.set_playhead(t)
        self._show_times()
        if was_playing:
            self.toggle_play()
        else:
            self._grab(t)

    # --- tocar o trecho ---------------------------------------------------

    def toggle_play(self) -> None:
        if self._playing:
            self.stop()
            return
        if not self.file:
            return
        pos = self.playhead if self.start <= self.playhead < self.end - 0.5 else self.start
        length = play_length(pos, self.end)
        if length <= 0:
            return
        self._token += 1
        self._playing = True
        self.play_btn.configure(text="⏸")
        self._background(self._prepare_playback, self._token, pos, length)

    def _prepare_playback(self, token: int, pos: float, length: float) -> None:
        """Em segundo plano: grava o som do trecho e começa a ler as imagens."""
        wav = self.dir / f"som{token}.wav"
        subprocess.run(sound_args(self.ffmpeg, self.file, pos, length, wav), capture_output=True,
                       creationflags=NO_WINDOW)
        proc = subprocess.Popen(frames_args(self.ffmpeg, self.file, pos, length), stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        self.events.put(("started", (token, pos, length, wav, proc)))
        index = 0
        while token == self._token:
            data = proc.stdout.read(FRAME_BYTES)
            if len(data) < FRAME_BYTES:
                return
            while token == self._token:
                try:
                    self._frames.put((token, index, data), timeout=0.2)
                    break
                except queue.Full:
                    continue
            index += 1

    def _on_started(self, payload) -> None:
        token, pos, length, wav, proc = payload
        if token != self._token:
            proc.kill()
            return
        self._proc, self._wav = proc, wav
        self._play_pos, self._play_len = pos, length
        if wav.exists():
            self.play_sound(wav)
        self._t0 = time.monotonic()

    def _advance(self) -> None:
        elapsed = time.monotonic() - self._t0
        if elapsed >= self._play_len:
            self.stop()
            self.playhead = min(self._play_pos + self._play_len, self.duration)
            self.timeline.set_playhead(self.playhead)
            self._show_times()
            return
        due, latest = due_frame(elapsed), None
        while True:
            frame = self._pending
            self._pending = None
            if frame is None:
                try:
                    frame = self._frames.get_nowait()
                except queue.Empty:
                    break
            if frame[0] != self._token:
                continue
            if frame[1] > due:
                self._pending = frame
                break
            latest = frame
        if latest:
            self._show(latest[2])
        self.playhead = self._play_pos + elapsed
        self.timeline.set_playhead(self.playhead)
        self._show_times()

    def stop(self) -> None:
        if not self._playing:
            return
        self._token += 1
        self._playing = False
        self._t0 = None
        self.play_btn.configure(text="▶")
        self.stop_sound()
        if self._proc:
            self._proc.kill()
            self._proc = None
        if self._wav:
            self._wav.unlink(missing_ok=True)
            self._wav = None
        self._pending = None

    # --- eventos -------------------------------------------------------

    def _tick(self) -> None:
        try:
            while True:
                try:
                    kind, payload = self.events.get_nowait()
                except queue.Empty:
                    break
                getattr(self, f"_on_{kind}")(payload)
            if self._playing and self._t0 is not None:
                self._advance()
        finally:
            if self.winfo_exists():
                self.after(TICK_MS, self._tick)

    def _on_progress(self, percent: float | None) -> None:
        self.note.configure(text=f"Preparando a prévia… {round(percent)}%" if percent else "Preparando a prévia…")

    def _on_ready(self, path: Path) -> None:
        self._job = None
        self._ready(path)

    def _on_failed(self, message: str) -> None:
        self._job = None
        self.note.configure(text=f"Sem prévia: {message}", text_color=ERROR_COLOR)

    def _on_frame(self, payload) -> None:
        seq, data = payload
        if seq == self._grab_seq and not self._playing:
            self._show(data)

    # --- ações -----------------------------------------------------------

    def _add(self, kind: Kind) -> None:
        """Confere os tempos, manda para a fila e fecha: o andamento aparece na fila da janela principal."""
        # vale o que está escrito nos campos, mesmo sem Enter (clicar no botão não tira o foco do campo)
        typed = (join_hms(*(e.get() for e in self.fields[w])) for w in ("start", "end"))
        try:
            start, end = check_range(*typed, self.duration)
        except ValueError as exc:
            self.range_label.configure(text=f"⚠ {exc}", text_color=ERROR_COLOR)
            return
        clip = as_clip(start, end, self.duration)
        self.close()
        self.on_add(kind, clip, self.info)

    def close(self) -> None:
        self.stop()
        if self._job:
            self._job.cancel()
        self.destroy()
