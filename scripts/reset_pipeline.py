"""
reset_pipeline.py — Utility to reset the pipeline state for fresh testing.
1. Deletes all generated ASANA tasks? No, we can't easily undo that right now.
2. Deletes the `outputs/accounts/` folder to clear extraction state.
3. Renames all `*.processed` files back to their original `.txt`/audio extensions so n8n can catch them again.
"""

import os
import shutil
from pathlib import Path

def reset_all():
    print("=== Resetting Clara AI Pipeline State ===")

    # 1. Delete extracted accounts (idempotency clears)
    accounts_dir = Path("outputs/accounts")
    if accounts_dir.exists():
        shutil.rmtree(accounts_dir)
        print(f"🗑️ Deleted generated outputs in: {accounts_dir}")

    # 2. Revert .processed marker files
    folders_to_check = [
        Path("dataset/demo_calls"),
        Path("dataset/onboarding_calls"),
        Path("outputs/transcripts/demo_calls"),
        Path("outputs/transcripts/onboarding_calls")
    ]

    revert_count = 0
    for folder in folders_to_check:
        if not folder.exists():
            continue
        for file_path in folder.glob("*.processed"):
            # Strip '.processed' from the end
            original_path = str(file_path)[:-10]
            os.replace(file_path, original_path)
            revert_count += 1
            print(f"[RESET] Reverted: {file_path.name} -> {Path(original_path).name}")

    print(f"\n[SUCCESS] Reset complete. Restored {revert_count} transcripts.")
    print("You can now trigger n8n or run_pipeline.py again as if it was the first time.")

if __name__ == "__main__":
    reset_all()
