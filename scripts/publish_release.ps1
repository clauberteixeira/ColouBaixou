# Publica uma versão nova no GitHub. Os programas instalados passam a avisar e se atualizar sozinhos.
# Uso: powershell -ExecutionPolicy Bypass -File scripts\publish_release.ps1 1.1.0
# Antes: atualize __version__ em src\ytdl\__init__.py, o CHANGELOG.md e crie docs\release-notes\v<versão>.md.
param([Parameter(Mandatory = $true)][string]$Version)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$current = (& "$root\.venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, 'src'); import ytdl; print(ytdl.__version__)").Trim()
if ($current -ne $Version) { throw "src\ytdl\__init__.py está em $current, não em $Version." }
$notes = Join-Path $root "docs\release-notes\v$Version.md"
if (-not (Test-Path $notes)) { throw "Crie as notas da versão em $notes." }
if (git status --porcelain) { throw "Há mudanças sem commit. Faça o commit antes de publicar." }

& "$root\.venv\Scripts\python.exe" -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Os testes falharam." }

& (Join-Path $PSScriptRoot "make_installer.ps1")
$installer = Join-Path $root "dist\installer\ColouBaixou-Setup-$Version.exe"

git tag "v$Version"
git push origin main "v$Version"
# o nome do arquivo (ColouBaixou-Setup-*.exe) e a tag (v<versão>) são o que o programa procura para se atualizar
gh release create "v$Version" $installer --title "ColouBaixô $Version" --notes-file $notes
Write-Host "Publicado: https://github.com/clauberteixeira/ColouBaixou/releases/tag/v$Version"
