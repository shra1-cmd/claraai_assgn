import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

LLM_MODE = os.getenv("LLM_MODE", "groq").lower()  # "groq" or "local"

# ── Groq setup (only imported when needed) ────────────────────────────────────
if LLM_MODE == "groq":
    from groq import Groq, RateLimitError
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

EXTRACTION_PROMPT = """
You are an expert business analyst. Extract structured information from this call transcript.
Return ONLY a valid JSON object with exactly these fields:

- account_id: null (will be set by the pipeline)
- company_name: Official business name
- business_hours: Object with keys: days (list), start_time (e.g. "9:00 AM"), end_time, timezone
- office_address: Full physical address
- services_supported: List of services offered
- emergency_definition: List of situations that qualify as emergencies
- emergency_routing_rules: How emergency calls are handled and routed
- non_emergency_routing_rules: How standard calls are handled
- call_transfer_rules: Object with timeout, retries, and fallback phrases
- integration_constraints: Software/system limitations mentioned (e.g. "never create X in Y system")
- after_hours_flow_summary: What happens when the office is closed
- office_hours_flow_summary: What happens during business hours
- questions_or_unknowns: List of missing or unclear items (empty list if nothing is unclear)
- notes: Any additional context worth preserving

If a field cannot be determined from the transcript, use null.

Transcript:
{transcript}
"""


def _call_groq(prompt: str) -> str:
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
    return _inner()


def _call_local(prompt: str) -> str:
    from local_extractor import extract_local
    return extract_local(prompt)


def _call_llm(prompt: str) -> str:
    """Route to Groq or local flan-t5 depending on LLM_MODE env var."""
    if LLM_MODE == "local":
        print("  [LocalLLM] Using flan-t5-base (offline mode)")
        return _call_local(prompt)
    return _call_groq(prompt)


def extract_memo(transcript_path: str, output_path: str, account_id: str) -> dict:
    """Extract a structured account memo from a transcript. Returns the memo dict."""
    with open(transcript_path, encoding="utf-8") as f:
        transcript = f.read()

    print(f"  Extracting memo for {account_id} [{LLM_MODE.upper()}]...")
    raw = _call_llm(EXTRACTION_PROMPT.format(transcript=transcript))

    try:
        memo = json.loads(raw)
    except json.JSONDecodeError:
        memo = {"error": "JSON parsing failed", "raw": raw}

    memo["account_id"] = account_id

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(memo, f, indent=2)

    print(f"  Memo saved → {output_path}")
    return memo