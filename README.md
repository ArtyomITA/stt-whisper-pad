# Whisper Pad STT

Desktop tool Windows per registrare dal microfono e trascrivere in locale con `faster-whisper`.

Non e una web app e non include modelli nel repository. Il modello STT viene scaricato automaticamente dalla cache Hugging Face al primo avvio, se non e gia presente.

## Setup

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

## Avvio GUI

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_gui.ps1
```

Funzioni:

- GUI desktop CustomTkinter
- registrazione microfono default Windows
- toggle `Rec / Stop`
- hotkey globale `Ctrl+M`
- trascrizione automatica dopo Stop
- testo copiabile, auto-copy, pulizia, salvataggio `.txt`
- storico sessione cliccabile

## Pre-download modello

Opzionale. Serve solo se vuoi scaricare/verificare Whisper prima di aprire la GUI.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_model.ps1
```

Default:

- model: `turbo`
- language: `it`
- VAD: enabled
- beam size: `1`

Puoi cambiare i default copiando `.env.example` in `.env`.

## File pesanti esclusi

La repo ignora:

- `.venv-stt/`
- `models/`
- `output/`
- cache Hugging Face create localmente
- formati modello come `.onnx`, `.gguf`, `.safetensors`, `.bin`, `.pt`
- audio generati come `.wav`, `.mp3`, `.flac`

Prima del push:

```powershell
git status --short
```

Non devono apparire modelli, venv, cache o audio registrati.

