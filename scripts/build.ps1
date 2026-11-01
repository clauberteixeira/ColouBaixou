# Gera dist\ColouBaixou\ com o FFmpeg leve e o yt-dlp embutidos.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Com o programa aberto o PyInstaller apaga parte de dist\ e depois falha, deixando o programa quebrado.
if (Get-Process "ColouBaixou", "YouTube Downloader" -ErrorAction SilentlyContinue) {
    throw "Feche o ColouBaixô antes de gerar o programa."
}

$ffmpegDir = Join-Path $root "vendor\ffmpeg"
if (-not (Test-Path (Join-Path $ffmpegDir "ffmpeg.exe"))) {
    & (Join-Path $PSScriptRoot "get_ffmpeg.ps1")
}
$ffmpeg = Join-Path $ffmpegDir "ffmpeg.exe"
$ffprobe = Join-Path $ffmpegDir "ffprobe.exe"

# sempre o mais recente: o programa só atualiza o motor depois de aberto
& (Join-Path $PSScriptRoot "get_ytdlp.ps1")
$ytdlp = Join-Path $root "vendor\ytdlp\yt-dlp.exe"

$icon = Join-Path $root "assets\icon.ico"
if (-not (Test-Path $icon)) { & "$root\.venv\Scripts\python.exe" scripts\make_icon.py }

& "$root\.venv\Scripts\pyinstaller.exe" --noconfirm --windowed --name "ColouBaixou" --icon $icon `
    --paths src --collect-data customtkinter --collect-data certifi `
    --add-binary "$ffmpeg;ffmpeg" --add-binary "$ffprobe;ffmpeg" --add-binary "$ytdlp;ytdlp" `
    --add-data "$icon;assets" `
    run_app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou ($LASTEXITCODE)" }

Write-Host "Pronto: $root\dist\ColouBaixou\ColouBaixou.exe"
