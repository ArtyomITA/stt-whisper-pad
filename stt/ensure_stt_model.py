# Preload local faster-whisper so the model is downloaded/cached if missing.
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


VOICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VOICE_ROOT))

from stt.stt_engine import SttEngine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure faster-whisper model is available locally.")
    parser.add_argument("--model", default=None, help="Model name, default from STT_MODEL_NAME or turbo.")
    args = parser.parse_args()

    try:
        engine = SttEngine(model_name=args.model)
        print(
            json.dumps(
                {
                    "ok": True,
                    "model": engine.model_name,
                    "device": engine.device,
                    "compute_type": engine.compute_type,
                    "load_seconds": engine.load_seconds,
                    "load_errors": engine.load_errors,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

