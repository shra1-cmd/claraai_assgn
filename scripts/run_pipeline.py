"""
run_pipeline.py — Clara AI Pipeline entry point.

Usage:
  python scripts/run_pipeline.py              # run both Pipeline A and B (default)
  python scripts/run_pipeline.py --mode a     # Pipeline A only: demo transcripts → v1
  python scripts/run_pipeline.py --mode b     # Pipeline B only: onboarding transcripts → v2

Triggered by:
  - Manual execution (development/testing)
  - n8n Pipeline A workflow  (demo transcript arrives)
  - n8n Pipeline B workflow  (onboarding transcript arrives)
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

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
        help="a=demo→v1 only, b=onboarding→v2 only, both=full pipeline (default)"
    )
    return parser.parse_args()


# ── Pipeline A: demo transcript → v1 ─────────────────────────────────────────

def run_pipeline_a(demo_paths: list[Path]):
    """Process demo transcripts → extract memo v1 + generate agent spec v1."""
    print("\n[ Pipeline A — Demo → v1 ]")
    print("-" * 50)

    for i, demo_path in enumerate(demo_paths):
        account_id    = f"acc{i + 1}"
        memo_v1_path  = f"outputs/accounts/{account_id}/v1/memo.json"
        agent_v1_path = f"outputs/accounts/{account_id}/v1/agent_spec.json"

        print(f"\n  Account: {account_id}")

        # ── IDEMPOTENCY GUARD ──────────────────────────────────────────────────
        # Uncomment the block below before final submission.
        # If v1 already exists, skip this account to prevent duplicate runs.
        #
        # if Path(memo_v1_path).exists():
        #     print(f"  SKIPPED {account_id} v1 (already exists)")
        #     print(f"  → Delete {memo_v1_path} to force regeneration")
        #     continue
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

        print(f"  Done — {account_id} v1")


# ── Pipeline B: onboarding transcript → v2 ───────────────────────────────────

def run_pipeline_b(onboard_paths: list[Path]):
    """Apply onboarding updates → patch memo to v2 + generate agent spec v2."""
    print("\n[ Pipeline B — Onboarding → v2 ]")
    print("-" * 50)

    for i, onboard_path in enumerate(onboard_paths):
        account_id    = f"acc{i + 1}"
        memo_v1_path  = f"outputs/accounts/{account_id}/v1/memo.json"
        memo_v2_path  = f"outputs/accounts/{account_id}/v2/memo.json"
        agent_v2_path = f"outputs/accounts/{account_id}/v2/agent_spec.json"

        print(f"\n  Account: {account_id}")

        # Pipeline B depends on v1 existing from Pipeline A
        if not Path(memo_v1_path).exists():
            print(f"  SKIPPED {account_id} — v1 memo not found. Run Pipeline A first.")
            continue

        # ── IDEMPOTENCY GUARD ──────────────────────────────────────────────────
        # Uncomment the block below before final submission.
        # If v2 already exists, skip this account to prevent duplicate runs.
        #
        # if Path(memo_v2_path).exists():
        #     print(f"  SKIPPED {account_id} v2 (already exists)")
        #     print(f"  → Delete {memo_v2_path} to force regeneration")
        #     continue
        # ──────────────────────────────────────────────────────────────────────

        print(f"  [B1] Applying onboarding patch ({onboard_path.name})...")
        apply_patch(memo_v1_path, str(onboard_path), account_id)

        print("  [B2] Generating agent spec v2...")
        generate_agent_spec(memo_v2_path, agent_v2_path)

        print("  Waiting 10s (rate limit)...")
        time.sleep(10)

        print(f"  Done — {account_id} v2")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_pipeline():
    args = _parse_args()

    print("=" * 50)
    print("  Clara AI Pipeline")
    print(f"  Mode: {'Pipeline A + B' if args.mode == 'both' else 'Pipeline ' + args.mode.upper()}")
    print("=" * 50)

    # Step 0: Ingest dataset → outputs/transcripts/
    demo_paths, onboard_paths = ingest_all()

    if not demo_paths:
        print("No demo transcripts found. Add files to dataset/demo_calls/ or outputs/transcripts/")
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