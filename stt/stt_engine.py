# Local faster-whisper STT engine.
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


VOICE_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(VOICE_ROOT / ".env", override=False)


class SttEngine:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv("STT_MODEL_NAME", "turbo")
        self.model = None
        self.device = ""
        self.compute_type = ""
        self.load_seconds = 0.0
        self.load_errors: list[dict[str, str]] = []
        self._load_model()

    def _load_model(self) -> None:
        from faster_whisper import WhisperModel

        attempts = [
            ("cuda", "int8_float16"),
            ("cuda", "int8"),
            ("cpu", "int8"),
        ]
        started = time.perf_counter()
        for device, compute_type in attempts:
            try:
                self.model = WhisperModel(
                    self.model_name,
                    device=device,
                    compute_type=compute_type,
                )
                self.device = device
                self.compute_type = compute_type
                self.load_seconds = time.perf_counter() - started
                return
            except Exception as exc:  # noqa: BLE001
                self.load_errors.append(
                    {
                        "device": device,
                        "compute_type": compute_type,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

        details = "; ".join(
            f"{e['device']}/{e['compute_type']}: {e['error']}" for e in self.load_errors
        )
        raise RuntimeError(f"Unable to load faster-whisper model '{self.model_name}'. {details}")

    def transcribe(
        self,
        audio_path: str | Path,
        language: str | None = None,
        vad_filter: bool | None = None,
        beam_size: int | None = None,
    ) -> dict[str, Any]:
        if self.model is None:
            raise RuntimeError("STT model not loaded")

        path = Path(audio_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        lang = language or os.getenv("STT_LANGUAGE", "it")
        vad = _env_bool("STT_VAD_FILTER", True) if vad_filter is None else vad_filter
        beam = int(os.getenv("STT_BEAM_SIZE", "1")) if beam_size is None else beam_size

        started = time.perf_counter()
        segments_iter, info = self.model.transcribe(
            str(path),
            language=lang,
            vad_filter=vad,
            beam_size=beam,
        )
        segments = [
            {
                "id": idx,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            }
            for idx, segment in enumerate(segments_iter)
        ]
        transcribe_seconds = time.perf_counter() - started
        text = " ".join(segment["text"] for segment in segments).strip()

        return {
            "text": text,
            "segments": segments,
            "language": getattr(info, "language", None),
            "language_probability": getattr(info, "language_probability", None),
            "timings": {
                "load_seconds": self.load_seconds,
                "transcribe_seconds": transcribe_seconds,
                "total_seconds": self.load_seconds + transcribe_seconds,
            },
            "model": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "vad_filter": vad,
            "beam_size": beam,
            "load_errors": self.load_errors,
        }


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
