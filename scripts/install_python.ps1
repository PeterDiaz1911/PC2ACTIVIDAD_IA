$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython)) {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        & py -3 -m venv (Join-Path $root '.venv')
    } else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCommand) {
            Write-Error 'No se encontró Python ni el lanzador py. Instala Python 3.10+ y vuelve a ejecutar npm run install:python.'
            exit 1
        }
        & $pythonCommand.Source -m venv (Join-Path $root '.venv')
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Error 'No se pudo crear .venv\Scripts\python.exe.'
    exit 1
}

Set-Location $root
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $venvPython -m pip check
exit $LASTEXITCODE
