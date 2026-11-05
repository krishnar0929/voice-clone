"""Shared helpers: config, ElevenLabs speech-to-text, and streaming text-to-speech playback."""
import io
import os
import queue
import threading
import wave

import numpy as np
import requests
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()

ELEVEN_BASE = "https://api.elevenlabs.io/v1"
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY", "")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
TTS_MODEL = os.getenv("TTS_MODEL", "eleven_flash_v2_5")
STT_MODEL = os.getenv("STT_MODEL", "scribe_v2")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")

TTS_RATE = 24000  # pcm_24000 = 16-bit mono PCM at 24 kHz
MIC_RATE = 16000


def require(*names):
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}")


# ---------- Speech to text ----------

def record_until_enter() -> bytes:
    """Record from the default mic until the user presses Enter. Returns WAV bytes."""
    frames = []

    def callback(indata, _frames, _time, _status):
        frames.append(indata.copy())

    with sd.InputStream(samplerate=MIC_RATE, channels=1, dtype="int16", callback=callback):
        input("  🎙  Recording... press Enter to stop ")
    if not frames:
        return b""
    audio = np.concatenate(frames)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(MIC_RATE)
        w.writeframes(audio.tobytes())
    return buf.getvalue()


def transcribe(wav_bytes: bytes) -> str:
    r = requests.post(
        f"{ELEVEN_BASE}/speech-to-text",
        headers={"xi-api-key": ELEVEN_KEY},
        data={"model_id": STT_MODEL},
        files={"file": ("speech.wav", wav_bytes, "audio/wav")},
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("text", "").strip()


# ---------- Text to speech (streaming) ----------

VOICE_SETTINGS = {
    "stability": 0.45,         # lower = more expressive
    "similarity_boost": 0.8,   # higher = closer to your real voice
    "style": 0.0,
    "use_speaker_boost": True,
}


def stream_tts(text: str, out: sd.RawOutputStream):
    """Stream one chunk of text in the cloned voice and play it as it arrives."""
    r = requests.post(
        f"{ELEVEN_BASE}/text-to-speech/{VOICE_ID}/stream",
        params={"output_format": f"pcm_{TTS_RATE}"},
        headers={"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"},
        json={"text": text, "model_id": TTS_MODEL, "voice_settings": VOICE_SETTINGS},
        stream=True,
        timeout=60,
    )
    r.raise_for_status()
    leftover = b""
    for chunk in r.iter_content(chunk_size=4096):
        data = leftover + chunk
        cut = len(data) - (len(data) % 2)  # keep 16-bit samples aligned
        if cut:
            out.write(data[:cut])
        leftover = data[cut:]


class Speaker:
    """Plays sentences in order on a background thread so Claude can keep streaming."""

    def __init__(self):
        self.q: "queue.Queue[str | None]" = queue.Queue()
        self.out = sd.RawOutputStream(samplerate=TTS_RATE, channels=1, dtype="int16")
        self.out.start()
        self.t = threading.Thread(target=self._run, daemon=True)
        self.t.start()

    def _run(self):
        while True:
            text = self.q.get()
            if text is None:
                break
            try:
                stream_tts(text, self.out)
            except Exception as e:  # keep going if one sentence fails
                print(f"\n  [TTS error] {e}")
            finally:
                self.q.task_done()

    def say(self, text: str):
        if text.strip():
            self.q.put(text.strip())

    def wait(self):
        self.q.join()

    def close(self):
        self.q.put(None)
        self.t.join()
        self.out.stop()
        self.out.close()
