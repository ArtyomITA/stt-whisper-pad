# CLI file transcription.
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VOICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VOICE_ROOT))

from stt.stt_engine import SttEngine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe audio file with faster-whisper.")
    parser.add_argument("--audio", required=True, help="Path to audio file.")
    parser.add_argument("--language", default=None, help="Language code, default from env or it.")
    parser.add_argument("--no-vad", action="store_true", help="Disable VAD filter.")
    parser.add_argument("--beam-size", type=int, default=None, help="Beam size, default 1.")
    args = parser.parse_args()

    try:
        engine = SttEngine()
        result = engine.transcribe(
            args.audio,
            language=args.language,
            vad_filter=not args.no_vad,
            beam_size=args.beam_size,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
