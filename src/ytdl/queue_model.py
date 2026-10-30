"""Regras da fila de downloads (sem interface)."""

import itertools
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Literal

from ytdl.formats import VideoInfo
from ytdl.progress import Progress

Kind = Literal["video", "audio"]


class Status(Enum):
    REVIEW = auto()       # colado, esperando o usuário conferir
    QUEUED = auto()       # liberado, aguardando a vez
    DOWNLOADING = auto()
    DONE = auto()
    ERROR = auto()
    CANCELLED = auto()


ACTIVE = {Status.REVIEW, Status.QUEUED, Status.DOWNLOADING}
FINISHED = {Status.DONE, Status.ERROR, Status.CANCELLED}
EDITABLE = {Status.REVIEW, Status.QUEUED}


@dataclass
class Item:
    id: int
    video_id: str
    kind: Kind
    status: Status
    checked: bool = True
    title: str | None = None
    channel: str | None = None
    duration: int | None = None
    info: VideoInfo | None = None
    res: int | None = None  # só vem da prévia
    progress: Progress | None = None
    error: str | None = None
    path: Path | None = None
    released_seq: int | None = field(default=None, repr=False)


class QueueModel:
    def __init__(self):
        self.items: list[Item] = []
        self._ids = itertools.count(1)
        self._release = itertools.count(1)

    def _is_duplicate(self, video_id: str, kind: Kind, ignore: Item | None = None) -> bool:
        return any(i is not ignore and i.video_id == video_id and i.kind == kind and i.status in ACTIVE
                   for i in self.items)

    def _queue(self, item: Item) -> None:
        item.status = Status.QUEUED
        item.released_seq = next(self._release)

    def add(self, video_id: str, kind: Kind, status: Status, **fields) -> Item | None:
        if self._is_duplicate(video_id, kind):
            return None
        item = Item(id=next(self._ids), video_id=video_id, kind=kind, status=Status.REVIEW, **fields)
        if status == Status.QUEUED:
            self._queue(item)
        self.items.append(item)
        return item

    def get(self, item_id: int) -> Item | None:
        return next((i for i in self.items if i.id == item_id), None)

    def set_kind(self, item_id: int, kind: Kind) -> bool:
        item = self.get(item_id)
        if not item or item.status not in EDITABLE or self._is_duplicate(item.video_id, kind, ignore=item):
            return False
        item.kind = kind
        return True

    def set_checked(self, item_id: int, checked: bool) -> bool:
        item = self.get(item_id)
        if not item or item.status != Status.REVIEW:
            return False
        item.checked = checked
        return True

    def review_checked_count(self) -> int:
        return sum(1 for i in self.items if i.status == Status.REVIEW and i.checked)

    def release_checked(self) -> int:
        released = [i for i in self.items if i.status == Status.REVIEW and i.checked]
        for item in released:
            self._queue(item)
        return len(released)

    def current(self) -> Item | None:
        return next((i for i in self.items if i.status == Status.DOWNLOADING), None)

    def next_item(self) -> Item | None:
        queued = [i for i in self.items if i.status == Status.QUEUED]
        return min(queued, key=lambda i: i.released_seq) if queued else None

    def start(self, item_id: int) -> None:
        item = self.get(item_id)
        if item and item.status == Status.QUEUED:
            item.status = Status.DOWNLOADING

    def finish(self, item_id: int, path: Path) -> None:
        if item := self.get(item_id):
            item.status, item.path, item.progress = Status.DONE, path, None

    def fail(self, item_id: int, message: str) -> None:
        if (item := self.get(item_id)) and item.status in ACTIVE:
            item.status, item.error, item.progress = Status.ERROR, message, None

    def mark_cancelled(self, item_id: int) -> None:
        if (item := self.get(item_id)) and item.status in ACTIVE:
            item.status, item.progress = Status.CANCELLED, None

    def requeue(self, item_id: int) -> None:
        """Devolve o item à fila na mesma posição (ex.: YouTube bloqueou temporariamente)."""
        if item := self.get(item_id):
            item.status, item.error, item.progress = Status.QUEUED, None, None

    def remove(self, item_id: int) -> Item | None:
        item = self.get(item_id)
        if item:
            self.items.remove(item)
        return item

    def cancel_all(self) -> Item | None:
        """Cancela os itens na fila; devolve o que está baixando (quem chama cancela o Job)."""
        for item in self.items:
            if item.status == Status.QUEUED:
                item.status = Status.CANCELLED
        return self.current()

    def clear_finished(self) -> int:
        before = len(self.items)
        self.items = [i for i in self.items if i.status not in FINISHED]
        return before - len(self.items)
