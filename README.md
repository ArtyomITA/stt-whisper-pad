# Whisper Pad

**A small Windows desktop app for local speech-to-text.**

Whisper Pad lets you press record, speak, stop, and immediately copy the transcription. It runs locally with `faster-whisper`, uses your default microphone, and does not ship model files in the repository.

Repository: `stt-whisper-pad`

## Why

Sometimes you do not need a full assistant, a cloud service, or a browser tab. You just need a clean little desktop window that turns your voice into text fast enough to paste it somewhere else.

Whisper Pad is built for that.

## Features

- Native desktop GUI, not a web app
- Local `faster-whisper` transcription
- Default Windows microphone recording
- `Rec / Stop` button
- Global `Ctrl+M` hotkey
- Auto-transcribe after stopping
- Copy button and optional auto-copy
- Save transcripts as `.txt`
- Session history you can click back into
- Dark, minimal CustomTkinter interface
- No model files committed to Git

## Quick Start

Requirements:

- Windows
- Python 3.11 recommended
- A working microphone
- Internet access on first model download

Clone the repo:

```powershell
git clone https://github.com/ArtyomITA/stt-whisper-pad.git
cd stt-whisper-pad
```

Set up the local environment:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Run the app:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_gui.ps1
```

First startup may take longer because Whisper has to download/cache the selected model.

## Usage

1. Open Whisper Pad.
2. Wait until the status says Whisper is ready.
3. Press `Rec` or `Ctrl+M`.
4. Speak.
5. Press `Stop` or `Ctrl+M`.
6. Copy, auto-copy, save, or reuse the transcript from the session history.

The last recording is saved locally as:

```text
output/last_mic.wav
```

Saved text transcripts go under:

```text
output/transcripts/
```

## Model Download

Whisper Pad does not upload large model files to GitHub.

By default it uses:

```text
STT_MODEL_NAME=turbo
STT_LANGUAGE=it
```

`faster-whisper` downloads and caches the model automatically when it is first loaded. If you want to pre-download/check the model before opening the GUI:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_model.ps1
```

## Configuration

Copy the example config:

```powershell
Copy-Item .\.env.example .\.env
```

Available defaults:

```env
STT_MODEL_NAME=turbo
STT_LANGUAGE=it
STT_VAD_FILTER=true
STT_BEAM_SIZE=1
```

Useful changes:

- set `STT_LANGUAGE=en` for English
- set `STT_MODEL_NAME=small` for a lighter model
- set `STT_MODEL_NAME=medium` for better quality on stronger hardware

## What Is Not Tracked

The repo intentionally ignores:

- `.venv-stt/`
- `models/`
- `output/`
- Hugging Face cache folders
- model formats such as `.onnx`, `.gguf`, `.safetensors`, `.bin`, `.pt`
- generated audio such as `.wav`, `.mp3`, `.flac`

This keeps the repository small and easy to clone.

## Privacy

Audio recording and transcription run on your machine. There is no app server and no cloud API call for transcription.

The only network access expected is the first model download through the normal Hugging Face/faster-whisper cache flow.

## Troubleshooting

If setup fails, make sure Python is available:

```powershell
py -3.11 --version
```

If the app cannot record, check:

- Windows microphone privacy permissions
- default input device
- whether another app is locking the microphone

If model loading is slow, that is usually the first download or CPU fallback. After the model is cached, startup should be faster.

## Development

Run a syntax check:

```powershell
.\.venv-stt\Scripts\python.exe -m py_compile .\gui\whisper_pad.py .\stt\stt_engine.py
```

Check imports:

```powershell
.\.venv-stt\Scripts\python.exe -c "import customtkinter, pynput, sounddevice, faster_whisper; print('ok')"
```

## License

No license has been selected yet. Add one before encouraging reuse or external contributions.
