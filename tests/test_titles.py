import re

import pytest

from ytdl.titles import TITLE_CLEANUPS, clean_title


@pytest.mark.parametrize("raw,clean", [
    ("Jorge & Mateus - Paredes (Como Sempre Feito Nunca) [Vídeo Oficial]", "Jorge & Mateus - Paredes"),
    ("Jorge & Mateus - Pergunta Boba - Part. Maestro Pinocchio (Ao Vivo Oficial)",
     "Jorge & Mateus - Pergunta Boba - Part. Maestro Pinocchio"),
    ("Humberto e Ronaldo - Pra lá de Bagdá/Parece Castigo | DVD #CopoSujo",
     "Humberto e Ronaldo - Pra lá de Bagdá/Parece Castigo"),
    ("Israel e Rodolffo - Coração de Quatro [Vídeo Oficial]", "Israel e Rodolffo - Coração de Quatro"),
    ("Música (feat. Anitta) [Clipe Oficial]", "Música (feat. Anitta)"),
    ("Dupla - Canção (Part. Fulano) (Ao Vivo)", "Dupla - Canção (Part. Fulano)"),
    ("Artista - Música - Vídeo Oficial", "Artista - Música"),
    ("Artist - Song (Official Music Video) HD", "Artist - Song"),
    ("Artista - Música | Letra", "Artista - Música"),
    ("Artista - Música #shorts #viral", "Artista - Música"),
    ("Panda - Eu te seguro  [ Panda sem Moderação 2 ]", "Panda - Eu te seguro"),
    ("Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film",
     "Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film"),
])
def test_clean_title(raw, clean):
    assert clean_title(raw) == clean


def test_never_empty():
    assert clean_title("[Vídeo Oficial]") == "[Vídeo Oficial]"
    assert clean_title("(Ao Vivo)") == "(Ao Vivo)"


def test_cleanup_rules_are_plain_regex_for_ytdlp():
    # as mesmas regras vão para o yt-dlp (--replace-in-metadata), para o título dentro do MP3
    for pattern, _ in TITLE_CLEANUPS:
        re.compile(pattern)
