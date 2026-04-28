$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$PythonExe = Join-Path $Root ".venv-stt\Scripts\python.exe"
$GuiScript = Join-Path $Root "gui\whisper_pad.py"

if (-not (Test-Path $PythonExe)) {
    throw "Missing STT venv Python: $PythonExe. Run .\scripts\setup.ps1 first."
}

& $PythonExe $GuiScript

