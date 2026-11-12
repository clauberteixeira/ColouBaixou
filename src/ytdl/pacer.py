"""Ritmo das consultas ao YouTube, para não cair no bloqueio "não sou um robô".

O YouTube recusa por horas a internet que consulta vídeos demais em pouco tempo. Aqui as
primeiras consultas passam na hora (colar um link continua instantâneo) e, depois, vai uma
a cada GAP_S segundos. O tempo parado sem consultar devolve as consultas rápidas.
"""

import math
import threading
import time
from typing import Callable

from ytdl.errors import Cancelled

GAP_S = 20.0  # 180 vídeos por hora no máximo
BURST = 3


class Pacer:
    def __init__(self, gap: float = GAP_S, burst: int = BURST,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep):
        self.gap, self.burst = gap, burst
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()
        self._due = clock()  # quando a fila de consultas "zera" (algoritmo de balde furado)

    def _reserve(self) -> float:
        """Guarda a vez desta consulta e devolve quando ela pode sair."""
        with self._lock:
            now = self._clock()
            self._due = max(self._due, now)
            start = max(now, self._due - self.gap * (self.burst - 1))
            self._due += self.gap
            return start

    def wait(self, on_wait: Callable[[int], None] = lambda seconds: None,
             cancelled: Callable[[], bool] = lambda: False) -> None:
        """Espera a vez; on_wait recebe os segundos que faltam (a cada segundo)."""
        start = self._reserve()
        while (left := start - self._clock()) > 0:
            if cancelled():
                raise Cancelled()
            on_wait(math.ceil(left))
            self._sleep(min(1.0, left))


YOUTUBE = Pacer()  # um só para o programa todo: vale para prévia, fila e playlist
