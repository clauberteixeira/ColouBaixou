"""Conexões HTTPS do programa."""

import ssl
import urllib.request
from functools import lru_cache

import certifi


@lru_cache(maxsize=1)
def https_context() -> ssl.SSLContext:
    """Confia nos certificados do Windows e na lista do certifi.

    O Windows só baixa um certificado raiz quando algo pede. Os navegadores têm lista própria,
    então num PC novo a internet funciona normalmente e mesmo assim faltam as raízes do GitHub.
    """
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def urlopen(url: str, timeout: float):
    return urllib.request.urlopen(url, timeout=timeout, context=https_context())
