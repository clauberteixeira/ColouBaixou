# Cria o atalho "YouTube Downloader" na área de trabalho.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$appDir = Join-Path $root "dist\YouTube Downloader"
$exe = Join-Path $appDir "YouTube Downloader.exe"
if (-not (Test-Path $exe)) { throw "Rode scripts\build.ps1 antes." }

$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path $desktop "YouTube Downloader.lnk"))
$link.TargetPath = $exe
$link.WorkingDirectory = $appDir
$link.Description = "Baixar vídeos (MP4) e áudios (MP3) do YouTube"
$link.Save()
Write-Host "Atalho criado em $desktop"
