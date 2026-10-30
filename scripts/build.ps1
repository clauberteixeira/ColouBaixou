# Gera dist\ColouBaixou\ com o FFmpeg leve embutido.
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

$icon = Join-Path $root "assets\icon.ico"
if (-not (Test-Path $icon)) { & "$root\.venv\Scripts\python.exe" scripts\make_icon.py }

& "$root\.venv\Scripts\pyinstaller.exe" --noconfirm --windowed --name "ColouBaixou" --icon $icon `
    --paths src --collect-data customtkinter `
    --add-binary "$ffmpeg;ffmpeg" --add-binary "$ffprobe;ffmpeg" `
    --add-data "$icon;assets" `
    run_app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou ($LASTEXITCODE)" }

Write-Host "Pronto: $root\dist\ColouBaixou\ColouBaixou.exe"
