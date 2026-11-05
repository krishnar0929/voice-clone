"""Local voice cloning with Chatterbox (open source, MIT) — runs on your Mac, no API key, nothing uploaded.

Chatterbox clones from a short reference clip at generation time (no training step).
It uses roughly the first 10 seconds of the reference, so pick your cleanest, most natural clip.

Usage:
    python chatterbox_test.py --ref ../voice_samples/nov4/wav/Clip16.wav
    python chatterbox_test.py --ref ../voice_samples/nov4/wav/Clip16.wav --text "Any sentence you like."
    python chatterbox_test.py --ref ../voice_samples/nov4/wav/Clip16.wav --file script.txt
    python chatterbox_test.py --ref ../voice_samples/nov4/wav/Clip16.wav --fish   # also make Fish versions to compare
    python chatterbox_test.py --pick ../voice_samples/nov4/wav                     # list clips by length to choose a reference
"""
import argparse
import subprocess
import sys
import time
import wave
from pathlib import Path

# The same test set every time, so different references and engines can be compared fairly.
TEST_SET = [
    ("casual", "So, honestly? I wasn't sure this would work. But, um, it actually sounds pretty close."),
    ("professional", "Good morning, everyone, and thanks for joining. Today I'll walk you through what we've built and why."),
    ("question", "Can I ask you something? What's the one task you do every week that you really hate?"),
    ("numbers", "We launched on October fifth, and by the end of the month we had close to two thousand users."),
    ("story", "Last month I pushed an update late at night. Next morning, five messages saying the app won't open. Lesson learned."),
]

OUT = Path("out")


def wav_seconds(path: Path) -> float:
    try:
        with wave.open(str(path)) as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0


def pick(folder: str):
    clips = sorted(Path(folder).glob("*.wav"))
    if not clips:
        sys.exit(f"No .wav files in {folder}")
    print("Good references are 10–20 s, clear, relaxed, no background noise:\n")
    for c in clips:
        s = wav_seconds(c)
        mark = "  <- good length" if 10 <= s <= 25 else ""
        print(f"  {c.name:14s} {s:5.1f}s{mark}")
    print("\nListen to a few (afplay <file>) and pass the best one with --ref.")


def load_model():
    try:
        import torch
        from chatterbox.tts import ChatterboxTTS
    except ImportError:
        sys.exit("Chatterbox isn't installed. See README → 'Local cloning (Chatterbox)'.")

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    # Chatterbox's checkpoints were saved on CUDA; map them to this Mac's device when loading.
    original_load = torch.load

    def load_on_device(*args, **kwargs):
        kwargs.setdefault("map_location", torch.device(device))
        return original_load(*args, **kwargs)

    torch.load = load_on_device
    print(f"Loading Chatterbox on {device} (first run downloads the model, a few GB)…")
    t0 = time.time()
    model = ChatterboxTTS.from_pretrained(device=device)
    print(f"Model ready in {time.time() - t0:.1f}s\n")
    return model


def generate(model, text, ref, out_file, exaggeration, cfg_weight):
    import torchaudio as ta

    t0 = time.time()
    wav = model.generate(text, audio_prompt_path=str(ref), exaggeration=exaggeration, cfg_weight=cfg_weight)
    took = time.time() - t0
    ta.save(str(out_file), wav, model.sr)
    audio_s = wav.shape[-1] / model.sr
    print(f"  ✅ {out_file}  ({audio_s:.1f}s of audio in {took:.1f}s)")


def fish_version(text, out_file):
    try:
        import fish_test
    except Exception as e:  # noqa: BLE001
        print(f"  (Fish skipped: {e})")
        return
    try:
        fish_test.say(text, fish_test.DEFAULT_MODEL, str(out_file), play=False)
    except SystemExit as e:
        print(f"  (Fish skipped: {e})")


def main():
    p = argparse.ArgumentParser(description="Clone your voice locally with Chatterbox")
    p.add_argument("--ref", help="Reference clip of your voice (.wav, ideally 10–20 s)")
    p.add_argument("--pick", metavar="FOLDER", help="List clips in FOLDER by length to choose a reference")
    p.add_argument("--text", help="Say one sentence instead of the test set")
    p.add_argument("--file", help="Read the text from a .txt file instead of the test set")
    p.add_argument("--exaggeration", type=float, default=0.5, help="Expressiveness, 0.25–1.0 (default 0.5)")
    p.add_argument("--cfg", type=float, default=0.5, help="Pacing/adherence, 0.3–0.7; lower = slower, calmer (default 0.5)")
    p.add_argument("--fish", action="store_true", help="Also generate each line with your Fish voice for side-by-side comparison")
    p.add_argument("--play", action="store_true", help="Play each result after generating (macOS)")
    a = p.parse_args()

    if a.pick:
        return pick(a.pick)
    if not a.ref:
        sys.exit("Pass --ref <your clip.wav>  (or --pick <folder> to choose one)")
    ref = Path(a.ref).expanduser()
    if not ref.exists():
        sys.exit(f"Reference not found: {ref}")

    if a.text:
        lines = [("custom", a.text)]
    elif a.file:
        lines = [("file", Path(a.file).read_text().strip())]
    else:
        lines = TEST_SET

    OUT.mkdir(exist_ok=True)
    model = load_model()
    tag = ref.stem.lower()
    for name, text in lines:
        print(f"[{name}] {text[:70]}{'…' if len(text) > 70 else ''}")
        cb = OUT / f"{name}-chatterbox-{tag}.wav"
        generate(model, text, ref, cb, a.exaggeration, a.cfg)
        if a.fish:
            fish_version(text, OUT / f"{name}-fish.mp3")
        if a.play and sys.platform == "darwin":
            subprocess.run(["afplay", str(cb)])

    print(f"\nDone. Files are in ./{OUT}/  — play them with: afplay out/<file>")


if __name__ == "__main__":
    main()
