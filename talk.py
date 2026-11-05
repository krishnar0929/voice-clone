"""Step 3: talk to Claude and hear the replies in your cloned voice.

Flow: mic -> ElevenLabs speech-to-text -> Claude (streaming) -> sentence chunks -> ElevenLabs Flash TTS -> speaker

Usage:
    python talk.py              # push-to-talk with your mic
    python talk.py --type       # type instead of speaking
"""
import argparse
import re
import time

import anthropic

from common import CLAUDE_MODEL, Speaker, record_until_enter, require, transcribe

SYSTEM_PROMPT = """You are speaking out loud through a text-to-speech voice.
Reply the way a friendly, confident person talks in conversation:
- short sentences, contractions, natural phrasing
- 1 to 4 sentences unless asked for more
- no markdown, lists, emojis, or code; spell out symbols and abbreviations
- write numbers the way they should be spoken"""

# Split after sentence-ending punctuation followed by a space (so "4.5" isn't split),
# letting speech start before Claude has finished the whole reply.
BOUNDARY = re.compile(r"[.!?;:](\s+)")
MIN_CHUNK = 25  # characters; very short chunks sound choppy


def take_chunk(buf: str):
    for m in BOUNDARY.finditer(buf):
        if m.end() >= MIN_CHUNK:
            return buf[: m.end()], buf[m.end():]
    return None, buf


def main():
    require("ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID")
    p = argparse.ArgumentParser()
    p.add_argument("--type", action="store_true", help="Type your messages instead of speaking")
    a = p.parse_args()

    client = anthropic.Anthropic()
    speaker = Speaker()
    history = []
    print(f"Model: {CLAUDE_MODEL}. Ctrl+C to quit.\n")

    try:
        while True:
            if a.type:
                user = input("You: ").strip()
            else:
                input("Press Enter to speak...")
                user = transcribe(record_until_enter())
                print(f"You: {user}")
            if not user:
                continue

            history.append({"role": "user", "content": user})
            t0 = time.time()
            first_audio = None
            buf, reply = "", ""
            print("Claude: ", end="", flush=True)

            with client.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=400,
                system=SYSTEM_PROMPT,
                messages=history,
            ) as stream:
                for text in stream.text_stream:
                    print(text, end="", flush=True)
                    buf += text
                    reply += text
                    # Send complete sentences to the voice as soon as they're ready
                    while True:
                        chunk, buf = take_chunk(buf)
                        if chunk is None:
                            break
                        speaker.say(chunk)
                        if first_audio is None:
                            first_audio = time.time() - t0
            speaker.say(buf)  # whatever is left
            print()
            if first_audio is not None:
                print(f"  (first sentence sent to voice after {first_audio:.2f}s)")
            speaker.wait()
            history.append({"role": "assistant", "content": reply})
    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        speaker.close()


if __name__ == "__main__":
    main()
