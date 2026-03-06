"""
transcribe.py — Ingest step for the Clara AI pipeline.

Responsibilities:
  1. Scan dataset/demo_calls/ and dataset/onboarding_calls/ for audio or text files.
  2. Audio files (.mp3, .wav, .m4a, .ogg) → run through local Whisper → save .txt to outputs/transcripts/
  3. Pre-transcribed text files (.txt) → copy directly to outputs/transcripts/
  4. Return the list of transcript paths so the pipeline can proceed.

Whisper model: 'base' — fast and accurate enough for call audio.
To use a higher quality model, change WHISPER_MODEL to 'small' or 'medium'.
"""

import os
import shutil
from pathlib import Path

DEMO_DIR       = Path("dataset/demo_calls")
ONBOARDING_DIR = Path("dataset/onboarding_calls")
TRANSCRIPT_DIR = Path("outputs/transcripts")
AUDIO_EXTS     = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
WHISPER_MODEL  = "base"

_whisper_model = None  # lazy-loaded only when audio files are found


def _get_whisper():
    """Lazy-load Whisper to avoid slow import when only .txt files are present."""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            print(f"Loading Whisper model '{WHISPER_MODEL}'...")
            _whisper_model = whisper.load_model(WHISPER_MODEL)
            print("Whisper ready.")
        except ImportError:
            raise RuntimeError(
                "Whisper not installed. Run: pip install openai-whisper\n"
                "Or provide .txt transcripts directly in dataset/ folders."
            )
    return _whisper_model


SKIP_FILENAMES = {"readme.txt", "readme.md", ".gitkeep"}  # files to never treat as data


def _ingest_folder(source_dir: Path, prefix: str) -> list[Path]:
    """
    Ingest all data files from source_dir.
    - .txt  (non-readme) → copy to outputs/transcripts/<prefix><N>.txt
    - audio → transcribe  → save to outputs/transcripts/<prefix><N>.txt
    If no data files found in source_dir, falls back to any existing
    outputs/transcripts/<prefix>*.txt files from a previous run.
    Returns list of transcript paths in sorted order.
    """
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    # Collect real data files (skip README and placeholder files)
    files = sorted([
        f for f in source_dir.iterdir()
        if (f.suffix.lower() in AUDIO_EXTS or f.suffix.lower() == ".txt")
        and f.name.lower() not in SKIP_FILENAMES
    ])

    # Fallback: if dataset/ is empty, use pre-existing transcripts
    if not files:
        existing = sorted(TRANSCRIPT_DIR.glob(f"{prefix}*.txt"))
        if existing:
            print(f"  No source files in {source_dir} — using {len(existing)} existing transcript(s) from outputs/transcripts/")
            return existing
        print(f"  No files found in {source_dir} and no existing transcripts.")
        return []

    transcript_paths = []
    for i, src in enumerate(files, start=1):
        dest = TRANSCRIPT_DIR / f"{prefix}{i}.txt"
        ext  = src.suffix.lower()

        if ext == ".txt":
            shutil.copy2(src, dest)
            print(f"  Copied  {src.name} → {dest.name}")

        elif ext in AUDIO_EXTS:
            print(f"  Transcribing {src.name} via Whisper...")
            model  = _get_whisper()
            result = model.transcribe(str(src))
            dest.write_text(result["text"], encoding="utf-8")
            print(f"  Saved   transcript → {dest.name}")

        else:
            print(f"  Skipped {src.name} (unsupported format)")
            continue

        transcript_paths.append(dest)

    return transcript_paths


def ingest_all() -> tuple[list[Path], list[Path]]:
    """
    Main entry point. Processes both demo and onboarding folders.
    Returns (demo_transcripts, onboarding_transcripts) as lists of Path objects.
    """
    print("=== Ingest Step ===")
    print(f"Demo folder:       {DEMO_DIR}")
    print(f"Onboarding folder: {ONBOARDING_DIR}")
    print(f"Transcripts out:   {TRANSCRIPT_DIR}")
    print()

    demo_paths      = _ingest_folder(DEMO_DIR,       prefix="demo")
    onboarding_paths = _ingest_folder(ONBOARDING_DIR, prefix="onboard")

    print(f"\nIngested: {len(demo_paths)} demo transcripts, {len(onboarding_paths)} onboarding transcripts.")
    return demo_paths, onboarding_paths


# Standalone usage: python scripts/transcribe.py
if __name__ == "__main__":
    demo, onboard = ingest_all()
    print("\nDemo transcripts:")
    for p in demo:
        print(f"  {p}")
    print("Onboarding transcripts:")
    for p in onboard:
        print(f"  {p}")