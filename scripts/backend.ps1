$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error 'No se encontró .venv\Scripts\python.exe. Ejecuta npm run install:python desde la raíz.'
    exit 1
}

$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)" -ErrorAction SilentlyContinue
    $command = if ($process) { $process.CommandLine } else { 'comando no disponible' }
    Write-Error "El puerto 8000 ya está ocupado por PID $($listener.OwningProcess): $command. No se detuvo el proceso; libera el puerto o cambia el puerto de FastAPI y el proxy."
    exit 1
}

Set-Location $root
& $python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
