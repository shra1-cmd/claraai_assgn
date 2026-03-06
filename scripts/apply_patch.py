import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=False)

LLM_MODE = os.getenv("LLM_MODE", "groq").lower()  # "groq" or "local"

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

if LLM_MODE == "groq":
    from groq import Groq, RateLimitError
    _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PATCH_PROMPT = """
You are an update extraction system.
Compare the onboarding transcript against the existing account memo.
Return ONLY a valid JSON object containing the fields that have changed or were previously null.
Do not include fields that are unchanged.

Existing Memo:
{memo}

Onboarding Transcript:
{transcript}
"""


def _call_groq(transcript: str, memo: dict) -> dict:
    prompt = PATCH_PROMPT.format(transcript=transcript, memo=json.dumps(memo, indent=2))

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5)
    )
    def _inner():
        return _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        ).choices[0].message.content
    return json.loads(_inner())


def _call_local(transcript: str, memo: dict) -> dict:
    from local_extractor import extract_local
    prompt = PATCH_PROMPT.format(transcript=transcript, memo=json.dumps(memo, indent=2))
    raw = extract_local(prompt)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "JSON parsing failed", "raw": raw}


def apply_patch(v1_path: str, transcript_path: str, account_id: str) -> dict:
    """
    Apply onboarding updates to a v1 memo.
    Writes memo v2 and a changes.md changelog to outputs/accounts/<account_id>/v2/.
    Returns the updated memo dict.
    """
    with open(v1_path, encoding="utf-8") as f:
        memo_v1 = json.load(f)

    with open(transcript_path, encoding="utf-8") as f:
        transcript = f.read()

    print(f"  Extracting onboarding updates for {account_id} [{LLM_MODE.upper()}]...")

    if LLM_MODE == "local":
        print("  [LocalLLM] Using flan-t5-base (offline mode)")
        updates = _call_local(transcript, memo_v1)
    else:
        updates = _call_groq(transcript, memo_v1)

    memo_v2 = {**memo_v1, **updates}

    v2_dir = Path(f"outputs/accounts/{account_id}/v2")
    v2_dir.mkdir(parents=True, exist_ok=True)

    with open(v2_dir / "memo.json", "w", encoding="utf-8") as f:
        json.dump(memo_v2, f, indent=2)

    # ── Human-readable changelog (changes.md) ────────────────────────────────
    changelog_lines = [f"# Changelog — {account_id} (v1 -> v2)\n"]
    for key, new_val in updates.items():
        old_val = memo_v1.get(key)
        changelog_lines.append(f"**{key}**\n- Before: {old_val}\n- After:  {new_val}\n")

    with open(v2_dir / "changes.md", "w", encoding="utf-8") as f:
        f.write("\n".join(changelog_lines))

    print(f"  Memo v2 and changelog saved -> {v2_dir}")
    return memo_v2