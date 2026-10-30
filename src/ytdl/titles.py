"""Limpa o título do vídeo para virar nome de arquivo (e título do MP3).

As regras são expressões regulares simples, aplicadas em ordem, para que o mesmo
conjunto vá ao yt-dlp (--replace-in-metadata) e o título dentro do MP3 saia igual.
"""

import re

_NOISE = (r"(?:v[ií]deo|clipe|clip|[áa]udio|lyric)\s+(?:oficial|official)"
          r"|official\s+(?:music\s+)?video|lyrics?\s+video|lyrics?|letra|visualizer|hd")

TITLE_CLEANUPS: list[tuple[str, str]] = [
    # (…) e […] — menos participações: (feat. X), (ft. X), (part. X), (com X)
    (r"(?i)\s*[(\[【]\s*(?!(?:feat|ft|part|participa[çc][ãa]o|com)\b)[^()\[\]【】]*[)\]】]", ""),
    (r"(?i)\s+[|｜].*$", ""),                                   # " | DVD …", " | Letra"
    (r"\s*#[\w-]+", ""),                                         # hashtags
    (rf"(?i)[\s\-–—.,]*\b(?:{_NOISE})\s*$", ""),                 # "- Vídeo Oficial" no fim
    (rf"(?i)[\s\-–—.,]*\b(?:{_NOISE})\s*$", ""),                 # (duas vezes: "Clipe Oficial HD")
    (r"\s{2,}", " "),
    (r"^[\s\-–—.,|]+|[\s\-–—.,|]+$", ""),
]
_COMPILED = [(re.compile(p), r) for p, r in TITLE_CLEANUPS]


def clean_title(title: str) -> str:
    cleaned = title
    for pattern, replacement in _COMPILED:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned if len(cleaned) >= 2 else title
