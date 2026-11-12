import pytest

from ytdl import pacer


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    """Nos testes, as consultas não esperam a vez (o ritmo real tem testes próprios)."""
    monkeypatch.setattr(pacer, "YOUTUBE", pacer.Pacer(gap=0))
