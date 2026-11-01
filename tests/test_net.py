import ssl

from ytdl.net import https_context


def _common_names(context: ssl.SSLContext) -> set[str]:
    return {value for cert in context.get_ca_certs() for rdn in cert["subject"] for key, value in rdn
            if key == "commonName"}


def test_trusts_github_roots_even_when_windows_has_none_of_them(monkeypatch):
    monkeypatch.setattr(ssl.SSLContext, "load_default_certs", lambda self, purpose=None: None)
    https_context.cache_clear()
    names = _common_names(https_context())
    https_context.cache_clear()
    assert {"ISRG Root X1", "USERTrust ECC Certification Authority"} <= names


def test_still_uses_windows_certificates(monkeypatch):
    # antivírus e redes de empresa instalam certificados próprios no Windows
    calls = []
    monkeypatch.setattr(ssl.SSLContext, "load_default_certs", lambda self, purpose=None: calls.append(purpose))
    https_context.cache_clear()
    https_context()
    https_context.cache_clear()
    assert calls
