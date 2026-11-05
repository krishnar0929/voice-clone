"""Step 1: create an Instant Voice Clone from your recordings and save its ID to .env.

Usage:
    python clone_voice.py samples/my-voice.m4a [samples/more.m4a ...] --name "Krishna"
"""
import argparse
import os
import re
from pathlib import Path

import requests

from common import ELEVEN_BASE, ELEVEN_KEY, require


def save_voice_id(voice_id: str):
    env = Path(".env")
    text = env.read_text() if env.exists() else ""
    line = f"ELEVENLABS_VOICE_ID={voice_id}"
    if re.search(r"^ELEVENLABS_VOICE_ID=.*$", text, flags=re.M):
        text = re.sub(r"^ELEVENLABS_VOICE_ID=.*$", line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    env.write_text(text)


def main():
    require("ELEVENLABS_API_KEY")
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+", help="Audio recordings of your voice (mp3/wav/m4a)")
    p.add_argument("--name", default="My Voice")
    p.add_argument("--description", default="Personal voice clone")
    p.add_argument("--denoise", action="store_true", help="Remove background noise (only if the recording is noisy)")
    a = p.parse_args()

    handles = [open(f, "rb") for f in a.files]
    try:
        r = requests.post(
            f"{ELEVEN_BASE}/voices/add",
            headers={"xi-api-key": ELEVEN_KEY},
            data={
                "name": a.name,
                "description": a.description,
                "remove_background_noise": str(a.denoise).lower(),
            },
            files=[("files", (os.path.basename(f.name), f)) for f in handles],
            timeout=180,
        )
    finally:
        for f in handles:
            f.close()

    if not r.ok:
        raise SystemExit(f"Clone failed ({r.status_code}): {r.text}")

    body = r.json()
    voice_id = body["voice_id"]
    save_voice_id(voice_id)
    print(f"✅ Voice cloned: {voice_id} (saved to .env)")
    if body.get("requires_verification"):
        print("⚠️  ElevenLabs wants you to verify this voice in the web app before using it.")


if __name__ == "__main__":
    main()
