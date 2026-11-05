# voice-clone

Clone your voice and generate natural speech from any text, using **Fish Audio S2.1 Pro** (recommended) or **ElevenLabs**. Includes a real-time talk mode where an AI model answers you out loud in your cloned voice.

| Script | What it does |
|---|---|
| `fish_test.py` | Fish Audio: create a private voice clone, then read text or a script file in that voice |
| `clone_voice.py` | ElevenLabs: create an Instant Voice Clone |
| `say.py` | ElevenLabs: read one line in your cloned voice |
| `talk.py` | Real-time conversation: mic → speech-to-text → AI reply (streaming) → your voice |

## 1. Install (macOS)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
open -e .env    # paste your API keys
```
The first time you record with `talk.py`, macOS asks Terminal for microphone access. Allow it.

## 2. Record a sample
Record 30–90 seconds of natural, relaxed speech in a quiet room (Voice Memos is fine). Talk the way you want the clone to sound, not like you're reading. Fish's free plan accepts up to 90 seconds; trim with:
```bash
ffmpeg -i natural.m4a -t 85 -c copy natural-85s.m4a
```

## 3. Fish Audio S2.1 Pro
Get an API key at https://fish.audio → Developer → API Keys and add `FISH_API_KEY` to `.env`.

Create the voice either on the website (My Voices → + → **Private**, then copy the ID from the URL into `FISH_VOICE_ID`) or with the script:
```bash
python fish_test.py clone samples/natural.m4a --name "My Voice"
```
API voice creation needs a funded API wallet; if you get "model creation limit reached (0/0)", create it on the website instead.

Read text in your voice:
```bash
python fish_test.py say "So, honestly? I wasn't sure this would work. But it sounds pretty close."
python fish_test.py say --file script.txt --out script.mp3
python fish_test.py say "Same line" --model s2-pro --out compare.mp3
```
Each run prints time-to-first-audio and plays the clip.

## 4. ElevenLabs (optional)
Add `ELEVENLABS_API_KEY` to `.env` (voice cloning needs the Starter plan or higher), then:
```bash
python clone_voice.py samples/natural.m4a --name "My Voice"
python say.py "Hi, this is my cloned voice. Does it sound like me?"
```

## 5. Talk mode (optional)
Add `ANTHROPIC_API_KEY` to `.env`, then:
```bash
python talk.py          # press Enter, speak, press Enter again
python talk.py --type   # type instead of speaking
```

## Making it sound natural
- Write text the way people talk: contractions, short sentences, commas for pauses, "..." for a thinking pause.
- Fish S2.1 understands emotion tags such as `(excited)`, `(laughing)`, `(thoughtful)`.
- Spell tricky names the way they're said, and write numbers out.
- `fish_test.py say --latency normal` (default) sounds more natural than `low`.
- A longer, varied, echo-free recording gives the biggest quality jump.

## Privacy
- `.env`, recordings and generated audio are git-ignored. Never commit API keys.
- Voices created by `fish_test.py` are **private** (Fish's default is public).
- Clone only your own voice or a voice you have permission to use, and use it only where listeners know they're hearing AI.
