# YouTube Downloader

Programa de Windows: cole o link de um vídeo do YouTube e baixe em **MP4** (até 4K, compatível com qualquer player) ou em **MP3** (320 kbps, com capa).

## Usar

Abra pelo atalho **YouTube Downloader** na área de trabalho. Se houver um link do YouTube copiado, ele já aparece colado.

Os arquivos vão para a pasta principal (padrão `Downloads\YouTube`, que pode ser trocada no ⚙):

```
Vídeos\<Canal>\<título>.mp4
Áudios\<Canal>\<título>.mp3
```

## Gerar o programa

Requisitos: Python 3.12, FFmpeg no PATH (`winget install Gyan.FFmpeg`) e Node.js (para liberar as qualidades acima de 1080p).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
powershell -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1
```

O resultado fica em `dist\YouTube Downloader\`. Para testar sem empacotar: `.\.venv\Scripts\python run_app.py`.

## Onde ficam os dados

`%LOCALAPPDATA%\YoutubeForDownload\`
- `bin\yt-dlp.exe`: motor de download, baixado na primeira execução e atualizado sozinho
- `config.json`: pasta principal escolhida
- `logs\app.log`: detalhes técnicos quando algo dá errado
- `tmp\`: arquivos temporários (limpos automaticamente)

## Observação

Use para vídeos seus, conteúdo liberado (Creative Commons) ou com permissão do autor. Os termos do YouTube não permitem baixar outros conteúdos sem autorização.
