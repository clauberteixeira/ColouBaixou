# ColouBaixô

Programa para Windows: cole o link de um vídeo do YouTube e baixe em **MP4** (até 4K, compatível com qualquer player) ou em **MP3** (320 kbps, com capa). Também baixa vários vídeos em fila e escolhe vídeos de playlists e Mix do YouTube.

## Instalar

1. Baixe `ColouBaixou-Setup-<versão>.exe` na página de [Releases](https://github.com/clauberteixeira/ColouBaixou/releases) e abra.
2. Se aparecer **"O Windows protegeu o computador"**, clique em **Mais informações → Executar assim mesmo**.
   - Outra forma: botão direito no instalador → **Propriedades** → marque **Desbloquear** → OK, e depois abra normalmente.
   - Copiado por **pendrive**, o aviso nem aparece.
3. Avançar → Instalar → Concluir. Não pede senha de administrador.

> **Por que aparece esse aviso?** O ColouBaixô é gratuito e feito para ajudar família e amigos, por isso não tem assinatura digital paga (que custa caro e precisa ser renovada todo ano). O Windows avisa sobre qualquer programa novo sem essa assinatura. Não é vírus nem defeito.

Funciona no Windows 10 e 11 (64 bits). Na primeira vez que abre, o programa baixa sozinho o motor de download (yt-dlp) e, se o computador não tiver Node.js, o Deno. Por isso a primeira abertura precisa de internet.

## Usar

- **Um vídeo:** cole o link, confira a prévia, escolha a qualidade e clique em **MP4** ou **MP3**.
- **Vários vídeos:** cole vários links de uma vez (um por linha). Eles entram na fila **em revisão**: desmarque o que não quiser e clique em **Baixar selecionados**.
- **Playlist ou Mix:** ao colar um link de playlist, o programa pergunta se você quer só aquele vídeo ou escolher vídeos da playlist.
- **Pasta:** aparece em "📁 Salvando em". Clique em **Alterar** para trocar, e a escolha fica gravada.

Arquivos salvos em:

```
<pasta>\Vídeos\<Canal>\<título>.mp4
<pasta>\Áudios\<Canal>\<título>.mp3
```

### Computadores diferentes

O programa testa o computador ao abrir e usa a aceleração de vídeo que existir (NVIDIA, Intel Quick Sync ou AMD). Num computador sem aceleração, **"Melhor disponível"** passa a ser a melhor qualidade que não precisa de conversão (normalmente 1080p), que é rápida em qualquer máquina. O 4K continua disponível com o aviso "(lenta neste PC)".

### "O YouTube bloqueou temporariamente"

Se forem feitos muitos downloads seguidos da mesma internet, o YouTube pode bloquear por algumas horas. A fila pausa sozinha. Clique em **▶ Continuar fila** mais tarde.

## Gerar o programa e o instalador

Requisitos: Python 3.12 e Inno Setup 6 (`winget install JRSoftware.InnoSetup`).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest
powershell -ExecutionPolicy Bypass -File scripts\make_installer.ps1
```

`scripts\get_ffmpeg.ps1` baixa o FFmpeg "essentials" para `vendor\ffmpeg\` (fora do git). O instalador sai em `dist\installer\`. Para testar sem empacotar: `.\.venv\Scripts\python run_app.py`. Para simular um computador sem Node.js ou sem aceleração, use as variáveis de ambiente `YTDL_NO_NODE=1` e `YTDL_NO_HW=1`.

## Onde ficam os dados

`%LOCALAPPDATA%\YoutubeForDownload\`
- `bin\`: yt-dlp e Deno, baixados e atualizados sozinhos
- `config.json`: pasta escolhida
- `logs\app.log`: detalhes técnicos quando algo dá errado
- `tmp\`: temporários (limpos automaticamente)

## Observação

Use para vídeos seus, conteúdo liberado (Creative Commons) ou com permissão do autor. Os termos do YouTube não permitem baixar outros conteúdos sem autorização.
