# Gera o programa e o instalador: dist\installer\ColouBaixou-Setup-<versão>.exe
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "build.ps1")

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
          "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 não encontrado (winget install JRSoftware.InnoSetup)." }

$version = (& "$root\.venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, 'src'); import ytdl; print(ytdl.__version__)").Trim()
& $iscc "/DAppVersion=$version" (Join-Path $root "installer\ColouBaixou.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falhou ($LASTEXITCODE)" }
Get-ChildItem (Join-Path $root "dist\installer") | Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,1)}}
