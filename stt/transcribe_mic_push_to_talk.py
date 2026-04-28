# Push-to-talk microphone transcription.
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

VOICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VOICE_ROOT))

from stt.stt_engine import SttEngine  # noqa: E402


def _default_input_device() -> tuple[int | None, int]:
    devices = sd.query_devices()
    inputs = [
        (idx, device)
        for idx, device in enumerate(devices)
        if int(device.get("max_input_channels", 0)) > 0
    ]
    if not inputs:
        raise RuntimeError("No microphone found. Check Windows input device permissions and drivers.")

    default = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else None
    if default is not None and default >= 0:
        info = sd.query_devices(default, "input")
        return int(default), int(info.get("default_samplerate", 16000))

    idx, info = inputs[0]
    return idx, int(info.get("default_samplerate", 16000))


def record_until_enter(output_path: Path) -> Path:
    device, samplerate = _default_input_device()
    frames: list[np.ndarray] = []

    def callback(indata, frame_count, time_info, status):  # noqa: ANN001, ARG001
        if status:
            print(status, file=sys.stderr)
        frames.append(indata.copy())

    input("Premi Enter per iniziare a registrare...")
    print("Registrazione attiva. Premi Enter per fermare.")
    with sd.InputStream(samplerate=samplerate, channels=1, dtype="float32", device=device, callback=callback):
        input()

    if not frames:
        raise RuntimeError("No audio captured from microphone.")

    audio = np.concatenate(frames, axis=0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, audio, samplerate)
    print(f"Saved {output_path} ({len(audio) / samplerate:.2f}s)")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Record microphone and transcribe with faster-whisper.")
    parser.add_argument("--output", default=str(VOICE_ROOT / "output" / "last_mic.wav"))
    args = parser.parse_args()

    try:
        wav_path = record_until_enter(Path(args.output))
        started = time.perf_counter()
        result = SttEngine().transcribe(wav_path)
        print(result["text"])
        print(f"Transcribe seconds: {time.perf_counter() - started:.2f}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
