import pytest

from ytdl.errors import NO_SPACE, error_for_live, friendly_error, tools_error

INTERNET = "Sem conexão com a internet. Verifique sua rede e tente de novo."
PRIVATE = "Este vídeo é privado e não pode ser baixado."
AGE = "Este vídeo tem restrição de idade e precisa de login. Isso não é suportado."
MEMBERS = "Este vídeo é exclusivo para membros do canal e não pode ser baixado."
UNAVAILABLE = "Este vídeo está indisponível ou foi removido."
BOT = "O YouTube bloqueou temporariamente o download. Tente mais tarde ou atualize o programa."
GENERIC = "Não foi possível baixar este vídeo. Tente atualizar o programa."


@pytest.mark.parametrize("output,message,update", [
    ("ERROR: [youtube] abc: Unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed>", INTERNET, False),
    ("ERROR: Failed to resolve 'www.youtube.com'", INTERNET, False),
    ("ERROR: [youtube] abc: Read timed out.", INTERNET, False),
    ("ERROR: [youtube] abc: Private video. Sign in if you've been granted access to this video", PRIVATE, False),
    ("ERROR: [youtube] abc: Sign in to confirm your age. This video may be inappropriate for some users.", AGE, False),
    ("ERROR: [youtube] abc: Join this channel to get access to members-only content like this video", MEMBERS, False),
    ("ERROR: [youtube] abc: Video unavailable. This video has been removed by the uploader", UNAVAILABLE, False),
    ("ERROR: [youtube] aaaaaaaaaaa: This video is unavailable", UNAVAILABLE, False),
    ("ERROR: unable to write data: [Errno 28] No space left on device", NO_SPACE.message, False),
    ("OSError: [WinError 112] Não há espaço suficiente no disco", NO_SPACE.message, False),
    ("ERROR: [youtube] abc: Sign in to confirm you're not a bot.", BOT, True),
    ("ERROR: something weird happened", GENERIC, True),
])
def test_friendly_error(output, message, update):
    err = friendly_error(output)
    assert (err.message, err.suggest_update) == (message, update)


def test_live_messages():
    assert error_for_live("is_live").message == "Transmissões ao vivo em andamento não podem ser baixadas."
    assert error_for_live("is_upcoming").message == "Esta transmissão ainda não começou."
    assert error_for_live("not_live") is None
    assert error_for_live(None) is None


@pytest.mark.parametrize("raw, expected", [
    ("<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed>", "data e a hora"),
    ("[WinError 5] Acesso negado: 'yt-dlp.exe.part' -> 'yt-dlp.exe'", "antivírus"),
    ("[WinError 32] O arquivo já está sendo usado por outro processo", "antivírus"),
    ("[Errno 13] Permission denied: 'yt-dlp.exe'", "antivírus"),
    ("FFmpeg não encontrado.", "Instale o ColouBaixô de novo"),
    ("<urlopen error [Errno 11001] getaddrinfo failed>", "Verifique a internet"),
    ("qualquer outra coisa", "Verifique a internet"),
])
def test_tools_error_says_what_to_do(raw, expected):
    assert expected in tools_error(raw)
