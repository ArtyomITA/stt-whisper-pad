$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Venv = Join-Path $Root ".venv-stt"
$Req = Join-Path $Root "requirements.txt"

function Test-Python311 {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if (-not $py) { return $false }
    & py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-Path $Venv)) {
    if (Test-Python311) {
        & py -3.11 -m venv $Venv
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) {
            throw "Python not found. Install Python 3.11, then rerun this script."
        }
        & $python.Source -m venv $Venv
    }
}

$VenvPython = Join-Path $Venv "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $Req

New-Item -ItemType Directory -Force -Path `
    (Join-Path $Root "models"), `
    (Join-Path $Root "output") | Out-Null

Write-Host "Setup complete."
Write-Host "Run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\run_gui.ps1"

