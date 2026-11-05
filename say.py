"""Step 2: quick test — speak any text in your cloned voice.

Usage:
    python say.py "Hi, this is my cloned voice. Does it sound like me?"
"""
import sys

from common import Speaker, require


def main():
    require("ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID")
    text = " ".join(sys.argv[1:]) or "Hi, I'm testing my cloned voice. Does this sound like me?"
    spk = Speaker()
    spk.say(text)
    spk.wait()
    spk.close()


if __name__ == "__main__":
    main()
