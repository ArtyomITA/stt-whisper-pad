$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$PythonExe = Join-Path $Root ".venv-stt\Scripts\python.exe"
$Script = Join-Path $Root "stt\ensure_stt_model.py"

if (-not (Test-Path $PythonExe)) {
    throw "Missing STT venv Python: $PythonExe. Run .\scripts\setup.ps1 first."
}

& $PythonExe $Script

