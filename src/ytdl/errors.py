"""Tradução das falhas do yt-dlp/ffmpeg para mensagens em português."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FriendlyError:
    message: str
    suggest_update: bool = False


class DownloadError(Exception):
    def __init__(self, friendly: FriendlyError):
        super().__init__(friendly.message)
        self.friendly = friendly


class Cancelled(Exception):
    pass


INVALID_LINK = FriendlyError("Este não parece ser um link de vídeo do YouTube.")
NO_SPACE = FriendlyError("Não há espaço suficiente no disco.")
NO_NODE_WARNING = (
    "Node.js não encontrado: vídeos acima de 1080p podem não aparecer. "
    "Instale o Node.js para liberar todas as qualidades."
)

BOT_BLOCK = FriendlyError(
    "O YouTube bloqueou temporariamente o download. Tente mais tarde ou atualize o programa.", True)

# Ordem importa: a primeira regra que bater vence.
RULES: list[tuple[tuple[str, ...], FriendlyError]] = [
    (("getaddrinfo failed", "failed to resolve", "unable to download webpage", "timed out", "no connection"),
     FriendlyError("Sem conexão com a internet. Verifique sua rede e tente de novo.")),
    (("private video",),
     FriendlyError("Este vídeo é privado e não pode ser baixado.")),
    (("sign in to confirm your age", "age-restricted"),
     FriendlyError("Este vídeo tem restrição de idade e precisa de login. Isso não é suportado.")),
    (("members-only", "join this channel"),
     FriendlyError("Este vídeo é exclusivo para membros do canal e não pode ser baixado.")),
    (("video unavailable", "video is unavailable", "has been removed", "this video is not available"),
     FriendlyError("Este vídeo está indisponível ou foi removido.")),
    (("no space left", "errno 28", "winerror 112"),
     NO_SPACE),
    (("not a bot",), BOT_BLOCK),
]
GENERIC = FriendlyError("Não foi possível baixar este vídeo. Tente atualizar o programa.", True)


def friendly_error(output: str) -> FriendlyError:
    text = output.lower()
    for needles, err in RULES:
        if any(n in text for n in needles):
            return err
    return GENERIC


def error_for_live(live_status: str | None) -> FriendlyError | None:
    if live_status == "is_live":
        return FriendlyError("Transmissões ao vivo em andamento não podem ser baixadas.")
    if live_status == "is_upcoming":
        return FriendlyError("Esta transmissão ainda não começou.")
    return None
