# Standalone desktop recorder/transcriber for local faster-whisper.
from __future__ import annotations

import queue
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import customtkinter as ctk
import numpy as np
import sounddevice as sd
import soundfile as sf
from pynput import keyboard


VOICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = VOICE_ROOT.parent
OUTPUT_DIR = VOICE_ROOT / "output"
LAST_MIC_WAV = OUTPUT_DIR / "last_mic.wav"
TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"

sys.path.insert(0, str(VOICE_ROOT))

from stt.stt_engine import SttEngine  # noqa: E402


@dataclass
class RecordingResult:
    path: Path
    duration_seconds: float
    samplerate: int
    device_name: str


class MicRecorder:
    def __init__(self) -> None:
        self.stream: sd.InputStream | None = None
        self.frames: list[np.ndarray] = []
        self.samplerate = 16000
        self.device_id: int | None = None
        self.device_name = "Microfono predefinito"
        self.started_at = 0.0
        self._lock = threading.Lock()

    def start(self) -> None:
        if self.stream is not None:
            raise RuntimeError("Recording is already active.")

        self.device_id, self.samplerate, self.device_name = self._default_input_device()
        self.frames = []
        self.started_at = time.perf_counter()

        def callback(indata: np.ndarray, frame_count: int, time_info: Any, status: sd.CallbackFlags) -> None:  # noqa: ARG001
            if status:
                print(status, file=sys.stderr)
            with self._lock:
                self.frames.append(indata.copy())

        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            dtype="float32",
            device=self.device_id,
            callback=callback,
        )
        self.stream.start()

    def stop(self, output_path: Path = LAST_MIC_WAV) -> RecordingResult:
        if self.stream is None:
            raise RuntimeError("Recording is not active.")

        stream = self.stream
        self.stream = None
        stream.stop()
        stream.close()

        with self._lock:
            frames = list(self.frames)
            self.frames = []

        if not frames:
            raise RuntimeError("No audio captured from microphone.")

        audio = np.concatenate(frames, axis=0)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, audio, self.samplerate)

        duration = len(audio) / float(self.samplerate)
        return RecordingResult(
            path=output_path,
            duration_seconds=duration,
            samplerate=self.samplerate,
            device_name=self.device_name,
        )

    def abort(self) -> None:
        if self.stream is None:
            return
        stream = self.stream
        self.stream = None
        try:
            stream.stop()
        finally:
            stream.close()

    @staticmethod
    def _default_input_device() -> tuple[int | None, int, str]:
        devices = sd.query_devices()
        inputs = [
            (idx, device)
            for idx, device in enumerate(devices)
            if int(device.get("max_input_channels", 0)) > 0
        ]
        if not inputs:
            raise RuntimeError("Nessun microfono trovato. Controlla permessi e driver audio Windows.")

        default = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else None
        if default is not None and default >= 0:
            info = sd.query_devices(default, "input")
            return int(default), int(info.get("default_samplerate", 16000)), str(info.get("name", "Microfono"))

        idx, info = inputs[0]
        return int(idx), int(info.get("default_samplerate", 16000)), str(info.get("name", "Microfono"))


class WhisperPad(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Jarvis Whisper Pad")
        self.geometry("1040x680")
        self.minsize(900, 560)

        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.engine: SttEngine | None = None
        self.recorder = MicRecorder()
        self.model_ready = False
        self.recording = False
        self.transcribing = False
        self.history: list[dict[str, Any]] = []
        self.hotkey_listener: keyboard.GlobalHotKeys | None = None
        self.record_started_at = 0.0

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Control-m>", lambda _event: self.events.put(("toggle_recording", None)))
        self.bind("<Control-M>", lambda _event: self.events.put(("toggle_recording", None)))

        self._start_hotkey()
        self._load_model_async()
        self.after(80, self._drain_events)
        self.after(150, self._tick_recording_timer)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="#111827", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=20, pady=16, sticky="w")
        ctk.CTkLabel(
            title_box,
            text="Whisper Pad",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_box,
            text="Ctrl+M registra/stop - locale, veloce, copiabile",
            text_color="#9CA3AF",
            font=ctk.CTkFont(size=13),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.grid(row=0, column=2, padx=20, pady=16, sticky="e")

        self.record_button = ctk.CTkButton(
            controls,
            text="Caricamento...",
            width=150,
            height=40,
            corner_radius=7,
            fg_color="#374151",
            hover_color="#4B5563",
            state="disabled",
            command=self._toggle_recording,
        )
        self.record_button.grid(row=0, column=0, padx=(0, 10))

        self.copy_button = ctk.CTkButton(
            controls,
            text="Copia",
            width=88,
            height=40,
            corner_radius=7,
            command=self._copy_text,
        )
        self.copy_button.grid(row=0, column=1, padx=(0, 10))

        self.clear_button = ctk.CTkButton(
            controls,
            text="Pulisci",
            width=88,
            height=40,
            corner_radius=7,
            fg_color="#1F2937",
            hover_color="#374151",
            command=self._clear_text,
        )
        self.clear_button.grid(row=0, column=2, padx=(0, 10))

        self.save_button = ctk.CTkButton(
            controls,
            text="Salva .txt",
            width=100,
            height=40,
            corner_radius=7,
            fg_color="#1F2937",
            hover_color="#374151",
            command=self._save_text,
        )
        self.save_button.grid(row=0, column=3, padx=(0, 12))

        self.auto_copy_var = ctk.BooleanVar(value=True)
        self.auto_copy_switch = ctk.CTkSwitch(
            controls,
            text="Auto-copy",
            variable=self.auto_copy_var,
            progress_color="#2563EB",
            button_color="#E5E7EB",
            button_hover_color="#FFFFFF",
        )
        self.auto_copy_switch.grid(row=0, column=4)

        body = ctk.CTkFrame(self, fg_color="#0B1120", corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_rowconfigure(0, weight=1)

        main = ctk.CTkFrame(body, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=(18, 10), pady=18)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            main,
            text="Caricamento Whisper...",
            anchor="w",
            text_color="#CBD5E1",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.status_label.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.textbox = ctk.CTkTextbox(
            main,
            wrap="word",
            border_width=1,
            border_color="#1F2937",
            fg_color="#111827",
            text_color="#F9FAFB",
            corner_radius=8,
            font=ctk.CTkFont(size=18),
            activate_scrollbars=True,
        )
        self.textbox.grid(row=1, column=0, sticky="nsew")
        self.textbox.insert("1.0", "Parla, ferma la registrazione, il testo apparira qui.")

        self.meta_label = ctk.CTkLabel(
            main,
            text="Model: turbo | Lingua: it | Hotkey globale: Ctrl+M",
            anchor="w",
            text_color="#64748B",
            font=ctk.CTkFont(size=12),
        )
        self.meta_label.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        side = ctk.CTkFrame(body, fg_color="#111827", corner_radius=8)
        side.grid(row=0, column=1, sticky="ns", padx=(8, 18), pady=18)
        side.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            side,
            text="Storico sessione",
            anchor="w",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))

        self.history_frame = ctk.CTkScrollableFrame(side, width=270, fg_color="#0F172A")
        self.history_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        footer = ctk.CTkFrame(self, fg_color="#111827", corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        self.footer_label = ctk.CTkLabel(
            footer,
            text="Pronto a caricare il modello...",
            anchor="w",
            text_color="#94A3B8",
            font=ctk.CTkFont(size=12),
        )
        self.footer_label.grid(row=0, column=0, sticky="ew", padx=18, pady=8)

    def _start_hotkey(self) -> None:
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys({"<ctrl>+m": self._hotkey_toggle})
            self.hotkey_listener.start()
        except Exception as exc:  # noqa: BLE001
            self.events.put(("error", f"Hotkey globale non attiva: {type(exc).__name__}: {exc}"))

    def _hotkey_toggle(self) -> None:
        self.events.put(("toggle_recording", None))

    def _load_model_async(self) -> None:
        def worker() -> None:
            try:
                engine = SttEngine()
                self.events.put(("model_ready", engine))
            except Exception as exc:  # noqa: BLE001
                self.events.put(("model_error", f"{type(exc).__name__}: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _toggle_recording(self) -> None:
        if self.recording:
            self._stop_recording()
            return
        self._start_recording()

    def _start_recording(self) -> None:
        if not self.model_ready:
            self._set_status("Whisper non e ancora pronto.", warn=True)
            return
        if self.transcribing:
            self._set_status("Trascrizione in corso, attendi un attimo.", warn=True)
            return

        try:
            self.recorder.start()
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Errore microfono: {type(exc).__name__}: {exc}", error=True)
            return

        self.recording = True
        self.record_started_at = time.perf_counter()
        self.record_button.configure(text="Stop", fg_color="#DC2626", hover_color="#B91C1C")
        self._set_status("Registrazione attiva...")
        self.footer_label.configure(text=f"Input: {self.recorder.device_name}")

    def _stop_recording(self) -> None:
        try:
            result = self.recorder.stop()
        except Exception as exc:  # noqa: BLE001
            self.recording = False
            self._reset_record_button()
            self._set_status(f"Errore salvataggio audio: {type(exc).__name__}: {exc}", error=True)
            return

        self.recording = False
        self._reset_record_button(disabled=True, text="Trascrivo...")
        self.transcribing = True
        self._set_status(f"Audio salvato ({result.duration_seconds:.1f}s). Trascrizione in corso...")
        self._transcribe_async(result)

    def _transcribe_async(self, recording: RecordingResult) -> None:
        def worker() -> None:
            try:
                if self.engine is None:
                    raise RuntimeError("STT model not loaded.")
                started = time.perf_counter()
                result = self.engine.transcribe(recording.path)
                elapsed = time.perf_counter() - started
                self.events.put(("transcription_ready", (recording, result, elapsed)))
            except Exception as exc:  # noqa: BLE001
                self.events.put(("transcription_error", f"{type(exc).__name__}: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _drain_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                self._handle_event(event, payload)
        except queue.Empty:
            pass
        self.after(80, self._drain_events)

    def _handle_event(self, event: str, payload: Any) -> None:
        if event == "toggle_recording":
            self._toggle_recording()
        elif event == "model_ready":
            self.engine = payload
            self.model_ready = True
            self._reset_record_button()
            self._set_status("Whisper pronto. Premi Rec o Ctrl+M.")
            self.footer_label.configure(
                text=f"Modello {payload.model_name} | device {payload.device} | compute {payload.compute_type}"
            )
            self.meta_label.configure(
                text=f"Model: {payload.model_name} | Device: {payload.device}/{payload.compute_type} | Lingua: it"
            )
        elif event == "model_error":
            self.model_ready = False
            self.record_button.configure(text="Errore", state="disabled", fg_color="#7F1D1D")
            self._set_status(f"Whisper non caricato: {payload}", error=True)
        elif event == "transcription_ready":
            recording, result, elapsed = payload
            self._show_transcription(recording, result, elapsed)
        elif event == "transcription_error":
            self.transcribing = False
            self._reset_record_button()
            self._set_status(f"Errore trascrizione: {payload}", error=True)
        elif event == "error":
            self._set_status(str(payload), warn=True)

    def _show_transcription(self, recording: RecordingResult, result: dict[str, Any], elapsed: float) -> None:
        self.transcribing = False
        self._reset_record_button()

        text = str(result.get("text", "")).strip()
        if not text:
            text = "[Nessun parlato rilevato]"

        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)

        if self.auto_copy_var.get() and not text.startswith("["):
            self._copy_text(silent=True)

        entry = {
            "text": text,
            "created_at": time.strftime("%H:%M:%S"),
            "duration": recording.duration_seconds,
            "elapsed": elapsed,
        }
        self.history.insert(0, entry)
        self.history = self.history[:12]
        self._render_history()

        self._set_status("Trascrizione pronta.")
        self.footer_label.configure(
            text=(
                f"Audio {recording.duration_seconds:.1f}s | STT {elapsed:.1f}s | "
                f"{result.get('device', '?')}/{result.get('compute_type', '?')} | {recording.path}"
            )
        )

    def _render_history(self) -> None:
        for child in self.history_frame.winfo_children():
            child.destroy()

        if not self.history:
            ctk.CTkLabel(
                self.history_frame,
                text="Nessuna trascrizione",
                text_color="#64748B",
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
            return

        for idx, item in enumerate(self.history):
            preview = " ".join(item["text"].split())
            if len(preview) > 80:
                preview = f"{preview[:77]}..."
            label = f"{item['created_at']}  {preview}"
            button = ctk.CTkButton(
                self.history_frame,
                text=label,
                anchor="w",
                height=42,
                corner_radius=6,
                fg_color="#1E293B",
                hover_color="#334155",
                command=lambda text=item["text"]: self._set_text(text),
            )
            button.grid(row=idx, column=0, sticky="ew", padx=6, pady=(6, 0))

    def _set_text(self, text: str) -> None:
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
        self._set_status("Trascrizione caricata dallo storico.")

    def _copy_text(self, silent: bool = False) -> None:
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            if not silent:
                self._set_status("Niente da copiare.", warn=True)
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        if not silent:
            self._set_status("Testo copiato negli appunti.")

    def _clear_text(self) -> None:
        self.textbox.delete("1.0", "end")
        self._set_status("Testo pulito.")

    def _save_text(self) -> None:
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            self._set_status("Niente da salvare.", warn=True)
            return

        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        path = TRANSCRIPTS_DIR / f"transcript_{time.strftime('%Y%m%d-%H%M%S')}.txt"
        path.write_text(text + "\n", encoding="utf-8")
        self._set_status(f"Salvato: {path}")

    def _reset_record_button(self, disabled: bool = False, text: str = "Rec") -> None:
        self.record_button.configure(
            text=text,
            state="disabled" if disabled else "normal",
            fg_color="#2563EB",
            hover_color="#1D4ED8",
        )

    def _set_status(self, text: str, warn: bool = False, error: bool = False) -> None:
        color = "#FCA5A5" if error else "#FBBF24" if warn else "#CBD5E1"
        self.status_label.configure(text=text, text_color=color)

    def _tick_recording_timer(self) -> None:
        if self.recording:
            elapsed = time.perf_counter() - self.record_started_at
            self.status_label.configure(text=f"Registrazione attiva... {elapsed:.1f}s")
        self.after(150, self._tick_recording_timer)

    def _close(self) -> None:
        try:
            self.recorder.abort()
        except Exception:
            pass
        if self.hotkey_listener is not None:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
        self.destroy()


def main() -> int:
    app = WhisperPad()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
