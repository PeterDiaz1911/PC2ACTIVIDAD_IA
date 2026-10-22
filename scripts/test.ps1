$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error 'No se encontró el entorno .venv. Ejecuta npm run install:python desde la raíz.'
    exit 1
}
Set-Location $root
& $python -m pytest -q tests
exit $LASTEXITCODE
