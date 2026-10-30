# Baixa o FFmpeg "essentials" (versão leve, do Gyan) para vendor\ffmpeg\.
# Tem tudo o que o programa usa: NVENC/QSV/AMF, libx264, zscale/tonemap e decodificador AV1.
$ErrorActionPreference = "Stop"
$version = "9.0.1"
$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root "vendor\ffmpeg"
$work = Join-Path $root "vendor\_dl\ffmpeg-ess"
$zip = Join-Path $work "ess.zip"

New-Item -ItemType Directory -Force $dest, $work | Out-Null
if (-not (Test-Path $zip)) {
    $url = "https://github.com/GyanD/codexffmpeg/releases/download/$version/ffmpeg-$version-essentials_build.zip"
    Write-Host "Baixando $url"
    Invoke-WebRequest $url -OutFile $zip -UseBasicParsing
}
Expand-Archive $zip -DestinationPath $work -Force
$bin = Get-ChildItem $work -Recurse -Filter ffmpeg.exe | Select-Object -First 1 | Split-Path
Copy-Item (Join-Path $bin "ffmpeg.exe"), (Join-Path $bin "ffprobe.exe") $dest -Force
Write-Host "FFmpeg em $dest"
