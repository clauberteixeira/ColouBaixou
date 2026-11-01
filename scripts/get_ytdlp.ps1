# Baixa a versão mais recente do yt-dlp para vendor\ytdlp\ (vai dentro do instalador).
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # a barra de progresso deixa o download muito lento
$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root "vendor\ytdlp"
$exe = Join-Path $dest "yt-dlp.exe"
$part = "$exe.part"
$url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"

New-Item -ItemType Directory -Force $dest | Out-Null
Write-Host "Baixando $url"
Invoke-WebRequest $url -OutFile $part -UseBasicParsing
Move-Item $part $exe -Force
Write-Host "yt-dlp $(& $exe --version) em $dest"
