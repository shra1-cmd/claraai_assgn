"""
compare_models.py — Side-by-side comparison of flan-t5-base (local) vs Groq API

Run: venv\Scripts\python.exe compare_models.py
"""

import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

TRANSCRIPT_FILE = "outputs/transcripts/demo2.txt"

with open(TRANSCRIPT_FILE, encoding="utf-8") as f:
    TRANSCRIPT = f.read()

# ── Run with Groq ─────────────────────────────────────────────────────────────
print("=" * 70)
print("  GROQ API  (llama-3.3-70b-versatile)  — cloud, fast, high quality")
print("=" * 70)

os.environ["LLM_MODE"] = "groq"
t0 = time.time()

from extract_memo import extract_memo
groq_memo = extract_memo(TRANSCRIPT_FILE, "/tmp/groq_test.json", "test_acc")
groq_time = round(time.time() - t0, 1)

print(f"\n  Done in {groq_time}s")

# ── Run with Local HuggingFace ────────────────────────────────────────────────
print()
print("=" * 70)
print("  LOCAL HuggingFace  (google/flan-t5-base)  — offline, free, ~250 MB")
print("=" * 70)

os.environ["LLM_MODE"] = "local"

# Need to reimport with new env var — reload module
import importlib
import extract_memo as em_module
importlib.reload(em_module)

t0 = time.time()
local_memo = em_module.extract_memo(TRANSCRIPT_FILE, "/tmp/local_test.json", "test_acc")
local_time = round(time.time() - t0, 1)

print(f"\n  Done in {local_time}s")

# ── Side-by-side comparison ───────────────────────────────────────────────────
FIELDS = [
    "company_name",
    "business_hours",
    "office_address",
    "services_supported",
    "emergency_definition",
    "emergency_routing_rules",
    "non_emergency_routing_rules",
    "after_hours_flow_summary",
    "integration_constraints",
]

print()
print("=" * 70)
print("  FIELD-BY-FIELD COMPARISON")
print("=" * 70)

groq_filled  = 0
local_filled = 0
groq_total   = len(FIELDS)
local_total  = len(FIELDS)

for field in FIELDS:
    g = groq_memo.get(field)
    l = local_memo.get(field)

    g_empty = g is None or g == [] or g == {}
    l_empty = l is None or l == [] or l == {}

    if not g_empty: groq_filled  += 1
    if not l_empty: local_filled += 1

    g_str = json.dumps(g)[:80]  if not g_empty else "❌  null / empty"
    l_str = json.dumps(l)[:80]  if not l_empty else "❌  null / empty"

    print(f"\n  📌 {field}")
    print(f"     GROQ  : {g_str}")
    print(f"     LOCAL : {l_str}")

# ── Summary table ─────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("  SUMMARY")
print("=" * 70)
print(f"  {'Metric':<30} {'Groq':>15} {'Local (flan-t5)':>18}")
print(f"  {'-'*63}")
print(f"  {'Fields populated':.<30} {groq_filled:>14}/{groq_total}  {local_filled:>14}/{local_total}")
print(f"  {'Time (seconds)':.<30} {groq_time:>15}  {local_time:>17}")
print(f"  {'Model size':.<30} {'~70B (cloud)':>15}  {'~250M (local)':>18}")
print(f"  {'Cost':.<30} {'Free tier':>15}  {'Free (offline)':>18}")
print(f"  {'Internet required':.<30} {'Yes':>15}  {'No':>18}")
print(f"  {'JSON reliability':.<30} {'Very high':>15}  {'Moderate':>18}")
print()
print("  ℹ️  Groq (llama-3.3-70b) is a 70B cloud model — far larger than flan-t5-base.")
print("  ℹ️  flan-t5-base uses field-by-field prompting to compensate for smaller size.")
print("  ℹ️  For production use → Groq. For offline/zero-dependency demo → Local.")
