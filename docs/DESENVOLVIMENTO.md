# Desenvolvimento

[← Voltar](../README.md)

## Como funciona

- **Interface:** Python 3.12 + [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter). As listas grandes (fila e playlist) usam `ttk.Treeview`, que aguenta milhares de linhas.
- **Download:** [yt-dlp](https://github.com/yt-dlp/yt-dlp) standalone (`yt-dlp.exe`), chamado como subprocesso. Ele é baixado para `%LOCALAPPDATA%\YoutubeForDownload\bin` e se atualiza com `-U`.
- **Runtime JavaScript do yt-dlp:** usa o Node.js se existir. Se não, baixa o [Deno](https://deno.com) na primeira execução.
- **Conversão:** [FFmpeg](https://ffmpeg.org) "essentials" (Gyan), embutido no programa.
  - O programa detecta o codificador por hardware nesta ordem: NVENC → Quick Sync → AMF → x264.
  - Só a NVIDIA libera "Melhor disponível" até 4K. Nos outros casos, ele prefere a versão H.264 que não precisa de conversão.
- **Empacotamento:** PyInstaller (pasta) + Inno Setup 6, com instalação por usuário (sem administrador).

```
src/ytdl/
  app.py              janela principal (prévia, fila, pasta)
  queue_model.py      regras da fila (sem interface, testado)
  queue_view.py       lista da fila (Treeview)
  playlist.py         leitura de playlists (--flat-playlist)
  playlist_window.py  pergunta e janela de escolha da playlist
  formats.py          escolha de formato/qualidade (até 4K, H.264/AAC, HDR→SDR)
  downloader.py       execução, conversão, cancelamento, oEmbed
  updater.py          atualização do próprio programa pelas Releases do GitHub
  about.py            nome, autor e links
  hardware.py         detecção de aceleração de vídeo
  commands.py         linhas de comando do yt-dlp/ffmpeg (puro)
  progress.py         leitura do progresso
  errors.py           mensagens de erro em português
  urls.py             links (um ou vários) e playlists
  paths.py, config.py, tools.py, settings.py
docs/superpowers/     documentos de desenho e planos de implementação
```

## Preparar o ambiente

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python run_app.py
```

Para simular outro computador:
- `YTDL_NO_NODE=1`: sem Node.js (força o uso do Deno);
- `YTDL_NO_HW=1`: sem aceleração de vídeo.

## Gerar o instalador

Requisito: [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`).

```powershell
powershell -ExecutionPolicy Bypass -File scripts\make_installer.ps1
```

Esse comando:
1. baixa o FFmpeg essentials para `vendor\ffmpeg\` (fora do git; `scripts\get_ffmpeg.ps1`);
2. gera o programa em `dist\ColouBaixou\` (`scripts\build.ps1`), e se recusa a rodar com o programa aberto;
3. gera o instalador `dist\installer\ColouBaixou-Setup-<versão>.exe` (`installer\ColouBaixou.iss`).

A versão fica em `src/ytdl/__init__.py`.

## Publicar uma versão (e atualizar todo mundo)

Os programas instalados consultam `api.github.com/repos/clauberteixeira/ColouBaixou/releases/latest` ao abrir (`src/ytdl/updater.py`). Quando a tag é maior que a versão instalada e a Release tem o arquivo `ColouBaixou-Setup-*.exe`, aparece a faixa **"Nova versão disponível"**. **Atualizar agora** baixa o instalador e roda em modo silencioso: ele fecha o programa, atualiza e reabre (`[Run] … Check: WizardSilent` no `.iss`).

1. Atualize `__version__` em `src/ytdl/__init__.py` (ex.: `1.1.0`).
2. Acrescente a versão no [CHANGELOG](../CHANGELOG.md) e crie `docs/release-notes/v1.1.0.md`.
3. Faça o commit.
4. Publique:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\publish_release.ps1 1.1.0
```

O script confere a versão, roda os testes, gera o instalador, cria a tag `v1.1.0`, envia para o GitHub e publica a Release com o instalador.
