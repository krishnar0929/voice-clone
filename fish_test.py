"""Simple Fish Audio S2.1 Pro test: clone your voice, then speak text with it.

Usage:
    python fish_test.py clone samples/my-voice.m4a --name "Krishna"
    python fish_test.py say "Hi, this is my cloned voice on Fish Audio."
    python fish_test.py say "Same line, different model" --model s2-pro
"""
import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.fish.audio"
KEY = os.getenv("FISH_API_KEY", "")
DEFAULT_MODEL = os.getenv("FISH_MODEL", "s2.1-pro")


def auth():
    if not KEY:
        sys.exit("Missing FISH_API_KEY in .env")
    return {"Authorization": f"Bearer {KEY}"}


def save_env(name: str, value: str):
    env = Path(".env")
    text = env.read_text() if env.exists() else ""
    line = f"{name}={value}"
    if re.search(rf"^{name}=.*$", text, flags=re.M):
        text = re.sub(rf"^{name}=.*$", line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    env.write_text(text)


def clone(files, name, transcript=None, enhance=False):
    handles = [open(f, "rb") for f in files]
    data = {
        "type": "tts",
        "title": name,
        "train_mode": "fast",
        "visibility": "private",  # default is PUBLIC — keep your voice private
    }
    if enhance:
        data["enhance_audio_quality"] = "true"  # only for noisy recordings; can sound processed
    if transcript:
        data["texts"] = transcript  # optional: what you said in the recording
    try:
        t0 = time.time()
        r = requests.post(
            f"{API}/model",
            headers=auth(),
            data=data,
            files=[("voices", (os.path.basename(f.name), f)) for f in handles],
            timeout=180,
        )
    finally:
        for f in handles:
            f.close()

    if not r.ok:
        sys.exit(f"Clone failed ({r.status_code}): {r.text}")
    voice_id = r.json()["_id"]
    save_env("FISH_VOICE_ID", voice_id)
    print(f"✅ Cloned in {time.time() - t0:.1f}s → FISH_VOICE_ID={voice_id} (saved to .env)")


def say(text, model, out="fish_output.mp3", play=True, latency="normal"):
    voice_id = os.getenv("FISH_VOICE_ID")
    if not voice_id:
        sys.exit("Missing FISH_VOICE_ID — run the clone command first")

    t0 = time.time()
    r = requests.post(
        f"{API}/v1/tts",
        headers={**auth(), "Content-Type": "application/json", "model": model},
        json={"text": text, "reference_id": voice_id, "format": "mp3", "mp3_bitrate": 192, "latency": latency},
        stream=True,
        timeout=60,
    )
    if not r.ok:
        sys.exit(f"TTS failed ({r.status_code}): {r.text}")

    first = None
    with open(out, "wb") as f:
        for chunk in r.iter_content(chunk_size=4096):
            if chunk and first is None:
                first = time.time() - t0
            f.write(chunk)
    total = time.time() - t0
    print(f"✅ {model}: first audio {first:.2f}s, full clip {total:.2f}s → {out}")

    if play and sys.platform == "darwin":
        subprocess.run(["afplay", out])


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("clone", help="Create a private voice clone from recordings")
    c.add_argument("files", nargs="+")
    c.add_argument("--name", default="My Voice")
    c.add_argument("--transcript", help="Optional text of what you said (improves accuracy)")
    c.add_argument("--enhance", action="store_true", help="Clean up a noisy recording (can sound processed)")

    s = sub.add_parser("say", help="Speak text in your cloned voice")
    s.add_argument("text", nargs="*", help="Text to speak (or use --file)")
    s.add_argument("--file", help="Read the text from a .txt file instead")
    s.add_argument("--model", default=DEFAULT_MODEL, help="s2.1-pro (default), s2-pro, drama-3")
    s.add_argument("--out", default="fish_output.mp3")
    s.add_argument("--no-play", action="store_true")
    s.add_argument("--latency", default="normal", choices=["normal", "balanced", "low"],
                   help="normal = most natural, low = fastest (sounds more robotic)")

    a = p.parse_args()
    if a.cmd == "clone":
        clone(a.files, a.name, a.transcript, a.enhance)
    else:
        text = Path(a.file).read_text().strip() if a.file else " ".join(a.text)
        if not text:
            sys.exit('Give some text, e.g. say "Hello there" or say --file script.txt')
        say(text, a.model, a.out, not a.no_play, a.latency)


if __name__ == "__main__":
    main()
