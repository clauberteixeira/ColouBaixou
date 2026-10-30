# Gera dist\YouTube Downloader\ com o ffmpeg embutido.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$ffmpeg = (Get-Command ffmpeg -ErrorAction Stop).Source
$ffprobe = (Get-Command ffprobe -ErrorAction Stop).Source
Write-Host "FFmpeg: $ffmpeg"

& "$root\.venv\Scripts\pyinstaller.exe" --noconfirm --windowed --name "YouTube Downloader" `
    --paths src --collect-data customtkinter `
    --add-binary "$ffmpeg;ffmpeg" --add-binary "$ffprobe;ffmpeg" `
    run_app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou ($LASTEXITCODE)" }

Write-Host "Pronto: $root\dist\YouTube Downloader\YouTube Downloader.exe"
