"""
run_pipeline.py — Clara AI Pipeline entry point.

Usage:
  python scripts/run_pipeline.py              # run both Pipeline A and B (default)
  python scripts/run_pipeline.py --mode a     # Pipeline A only: demo transcripts -> v1
  python scripts/run_pipeline.py --mode b     # Pipeline B only: onboarding transcripts -> v2

Triggered by:
  - Manual execution (development/testing)
  - n8n Pipeline A workflow  (demo transcript arrives)
  - n8n Pipeline B workflow  (onboarding transcript arrives)
"""

import os
import sys
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback for older python versions if needed
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
import time
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Force Groq mode early so imports pick it up properly
os.environ["LLM_MODE"] = "groq"

sys.path.insert(0, str(Path(__file__).parent))

from extract_memo import extract_memo
from generate_agent import generate_agent_spec
from apply_patch import apply_patch
from task_tracker import create_asana_task
from transcribe import ingest_all

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args():
    parser = argparse.ArgumentParser(description="Clara AI Pipeline")
    parser.add_argument(
        "--mode",
        choices=["a", "b", "both"],
        default="both",
        help="a=demo->v1 only, b=onboarding->v2 only, both=full pipeline (default)"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Specific transcript file to process (used by n8n file triggers)"
    )
    return parser.parse_args()


# ── Pipeline A: demo transcript -> v1 ─────────────────────────────────────────

def run_pipeline_a(demo_paths: list[Path]):
    """Process demo transcripts -> extract memo v1 + generate agent spec v1."""
    print("\n[ Pipeline A — Demo -> v1 ]")
    print("-" * 50)

    for demo_path in demo_paths:
        # Derive account ID from filename (e.g., demo3.txt -> acc3)
        num = "".join(filter(str.isdigit, demo_path.stem))
        account_id = f"acc{num}" if num else demo_path.stem

        memo_v1_path  = f"outputs/accounts/{account_id}/v1/memo.json"
        agent_v1_path = f"outputs/accounts/{account_id}/v1/agent_spec.json"

        print(f"\n  Account: {account_id}")

        # ── IDEMPOTENCY GUARD ──────────────────────────────────────────────────
        if Path(memo_v1_path).exists():
            print(f"  SKIPPED {account_id} v1 (already exists)")
            
            # Ensure it is marked processed even if skipped
            if not str(demo_path).endswith(".processed"):
                processed_path = demo_path.with_name(demo_path.name + ".processed")
                os.replace(demo_path, processed_path)
            continue
        # ──────────────────────────────────────────────────────────────────────

        print("  [A1] Extracting memo v1...")
        memo_data = extract_memo(str(demo_path), memo_v1_path, account_id)

        # Create Asana follow-up task for any unknowns or notes
        unknowns = memo_data.get("questions_or_unknowns")
        notes    = memo_data.get("notes")
        if unknowns or notes:
            details = f"Follow-up needed:\n{json.dumps(unknowns)}\n\nNotes:\n{notes}"
            print(f"  [Asana] Creating task for {account_id}...")
            create_asana_task(memo_data.get("company_name", account_id), details)

        print("  [A2] Generating agent spec v1...")
        generate_agent_spec(memo_v1_path, agent_v1_path)

        print("  Waiting 10s (rate limit)...")
        time.sleep(10)

        # ── MARKER ─────────────────────────────────────────────────────────────
        if not str(demo_path).endswith(".processed"):
            processed_path = demo_path.with_name(demo_path.name + ".processed")
            os.replace(demo_path, processed_path)
            print(f"  [Marker] Renamed to {processed_path.name}")
        # ──────────────────────────────────────────────────────────────────────

        print(f"  Done — {account_id} v1")


# ── Pipeline B: onboarding transcript -> v2 ───────────────────────────────────

def run_pipeline_b(onboard_paths: list[Path]):
    """Apply onboarding updates -> patch memo to v2 + generate agent spec v2."""
    print("\n[ Pipeline B — Onboarding -> v2 ]")
    print("-" * 50)

    for onboard_path in onboard_paths:
        # Derive account ID from filename (e.g., onboard3.txt -> acc3)
        num = "".join(filter(str.isdigit, onboard_path.stem))
        account_id = f"acc{num}" if num else onboard_path.stem

        memo_v1_path  = f"outputs/accounts/{account_id}/v1/memo.json"
        memo_v2_path  = f"outputs/accounts/{account_id}/v2/memo.json"
        agent_v2_path = f"outputs/accounts/{account_id}/v2/agent_spec.json"

        print(f"\n  Account: {account_id}")

        # Pipeline B depends on v1 existing from Pipeline A
        if not Path(memo_v1_path).exists():
            print(f"  SKIPPED {account_id} — v1 memo not found. Run Pipeline A first.")
            continue

        # ── IDEMPOTENCY GUARD ──────────────────────────────────────────────────
        if Path(memo_v2_path).exists():
            print(f"  SKIPPED {account_id} v2 (already exists)")
            
            if not str(onboard_path).endswith(".processed"):
                processed_path = onboard_path.with_name(onboard_path.name + ".processed")
                os.replace(onboard_path, processed_path)
            continue
        # ──────────────────────────────────────────────────────────────────────

        print(f"  [B1] Applying onboarding patch ({onboard_path.name})...")
        apply_patch(memo_v1_path, str(onboard_path), account_id)

        print("  [B2] Generating agent spec v2...")
        generate_agent_spec(memo_v2_path, agent_v2_path)

        print("  Waiting 10s (rate limit)...")
        time.sleep(10)

        # ── MARKER ─────────────────────────────────────────────────────────────
        if not str(onboard_path).endswith(".processed"):
            processed_path = onboard_path.with_name(onboard_path.name + ".processed")
            os.replace(onboard_path, processed_path)
            print(f"  [Marker] Renamed to {processed_path.name}")
        # ──────────────────────────────────────────────────────────────────────

        print(f"  Done — {account_id} v2")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_pipeline():
    args = _parse_args()

    print("=" * 50)
    print("  Clara AI Pipeline")
    print(f"  Mode: {'Pipeline A + B' if args.mode == 'both' else 'Pipeline ' + args.mode.upper()}")
    print("=" * 50)

    # ── N8N SINGLE FILE TRIGGER MODE ──────────────────────────────────────────
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return
            
        # Step 1: Ingest the single file to the central hub
        import shutil
        from transcribe import _get_whisper, AUDIO_EXTS
        
        path_lower = str(file_path).lower()
        sub_folder = "demo_calls" if "demo" in path_lower else "onboarding_calls"
        
        dest_path = Path("outputs/transcripts") / sub_folder / (file_path.stem + ".txt")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if file_path.suffix.lower() == ".txt":
            if file_path.resolve() != dest_path.resolve():
                shutil.copy2(file_path, dest_path)
        elif file_path.suffix.lower() in AUDIO_EXTS:
            print(f"  Transcribing {file_path.name} via Whisper...")
            model = _get_whisper()
            result = model.transcribe(str(file_path))
            dest_path.write_text(result["text"], encoding="utf-8")
        else:
            print(f"  Unsupported file type: {file_path.name}")
            return
            
        print(f"\n  Automated Event Trigger: {file_path.name} -> {dest_path.parent.name}/{dest_path.name}")
        
        # Step 2: Route the central hub file through the pipeline
        if "demo" in path_lower:
            run_pipeline_a([dest_path])
        elif "onboard" in path_lower:
            run_pipeline_b([dest_path])
        else:
            print("  Unknown file type. Path must contain 'demo' or 'onboard'.")
            
        # Step 3: Mark the original source file so it's globally ignored
        if not str(file_path).endswith(".processed"):
            src_processed = file_path.with_name(file_path.name + ".processed")
            if file_path.exists():
                os.replace(file_path, src_processed)
                print(f"  [Marker] Source marked: {src_processed.name}")
        
        print("\n==================================================")
        print("  Automation completed.")
        print("==================================================")
        return

    # ── MANUAL BATCH MODE ─────────────────────────────────────────────────────
    # Step 0: Ingest dataset -> outputs/transcripts/
    demo_paths, onboard_paths = ingest_all()

    # Filter out already processed files if any leaked through
    demo_paths = [p for p in demo_paths if not str(p).endswith(".processed")]
    onboard_paths = [p for p in onboard_paths if not str(p).endswith(".processed")]

    if not demo_paths and not onboard_paths:
        print("No new transcripts to process.")
        return

    print(f"\n  {len(demo_paths)} demo + {len(onboard_paths)} onboarding transcripts ready.")

    if args.mode in ("a", "both"):
        run_pipeline_a(demo_paths)

    if args.mode in ("b", "both"):
        run_pipeline_b(onboard_paths)

    print()
    print("=" * 50)
    print("  Pipeline complete.")
    print("=" * 50)


if __name__ == "__main__":
    run_pipeline()