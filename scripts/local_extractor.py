"""
local_extractor.py — Zero-cost, offline LLM backend using google/flan-t5-base.

Strategy: flan-t5-base (250M params) cannot reliably produce a 14-field JSON
in one shot. Instead we ask one targeted question per field and assemble the
memo dict afterwards. Each question is short enough for the model to answer well.

Model is downloaded once (~250 MB) and cached at:
  Windows: C:/Users/<user>/.cache/huggingface/hub/
  After first download → runs fully offline, no internet required.

Set LLM_MODE=local in your .env to activate.
Set LLM_MODE=groq (default) to use the Groq API instead.
"""

from __future__ import annotations
import json

MODEL_NAME = "google/flan-t5-base"

_model     = None
_tokenizer = None


def _load_model():
    """Load flan-t5-base once and keep in memory for subsequent calls."""
    global _model, _tokenizer
    if _model is None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        print(f"  [LocalLLM] Loading {MODEL_NAME} (downloads ~250 MB on first run)...")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model     = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
        print(f"  [LocalLLM] {MODEL_NAME} ready — running offline from cache.")
    return _model, _tokenizer


def _ask(question: str, context: str) -> str:
    """Ask a single targeted question about the transcript context."""
    model, tokenizer = _load_model()

    # Truncate context to fit model's 512-token limit
    ctx = context[:1500]
    prompt = f"Question: {question}\n\nContext: {ctx}\n\nAnswer:"

    inputs  = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    outputs = model.generate(**inputs, max_new_tokens=100, num_beams=4, do_sample=False)
    return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()


def _ask_list(question: str, context: str) -> list[str]:
    """Ask a question expected to return a comma-separated list."""
    raw = _ask(question, context)
    if not raw or raw.lower() in ("none", "unknown", "n/a", "not mentioned"):
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def extract_local(prompt: str) -> str:
    """
    Extract structured account data from a transcript using field-by-field questions.
    Returns a JSON string with the same 14 fields as the Groq extraction.
    The 'prompt' argument is the full transcript text (the caller passes the prompt
    from extract_memo.py, but we extract the transcript portion from it).
    """
    # Extract just the transcript text from the combined prompt
    transcript = prompt
    if "Transcript:" in prompt:
        transcript = prompt.split("Transcript:", 1)[-1].strip()

    print("  [LocalLLM] Running field-by-field extraction (flan-t5-base)...")

    ctx = transcript  # alias for readability

    company    = _ask("What is the official company name?", ctx)
    address    = _ask("What is the full office address?", ctx)
    days       = _ask_list("What days of the week are they open?", ctx)
    start_time = _ask("What time does the office open?", ctx)
    end_time   = _ask("What time does the office close?", ctx)
    timezone   = _ask("What timezone are the business hours in?", ctx)
    services   = _ask_list("What services does the company offer? List them.", ctx)
    emerg_def  = _ask_list("What situations count as emergencies for this company?", ctx)
    emerg_rout = _ask("How are emergency calls routed or handled?", ctx)
    non_emerg  = _ask("How are non-emergency calls handled?", ctx)
    after_hrs  = _ask("What happens when someone calls after business hours?", ctx)
    during_hrs = _ask("What happens when someone calls during business hours?", ctx)
    constraints = _ask("Are there any software or system constraints mentioned?", ctx)
    notes      = _ask("Are there any other important notes or context?", ctx)

    memo = {
        "account_id": None,
        "company_name": company if company.lower() not in ("unknown", "none", "n/a") else None,
        "business_hours": {
            "days":       days,
            "start_time": start_time,
            "end_time":   end_time,
            "timezone":   timezone
        },
        "office_address":           address  if address.lower()   not in ("unknown", "none") else None,
        "services_supported":       services,
        "emergency_definition":     emerg_def,
        "emergency_routing_rules":  emerg_rout,
        "non_emergency_routing_rules": non_emerg,
        "call_transfer_rules":      None,
        "integration_constraints":  constraints if constraints.lower() not in ("none", "n/a", "unknown") else None,
        "after_hours_flow_summary": after_hrs,
        "office_hours_flow_summary": during_hrs,
        "questions_or_unknowns":    [],
        "notes":                    notes if notes.lower() not in ("none", "n/a", "unknown") else None,
    }

    return json.dumps(memo)


# Standalone test
if __name__ == "__main__":
    print("=" * 60)
    print("Local LLM Test — google/flan-t5-base (field-by-field mode)")
    print("=" * 60)

    sample = """
    This is a transcript of a demo call with ABC Plumbing.
    We are open Monday through Friday, 9 AM to 5 PM Pacific Time.
    Our office is at 123 Main Street, Portland, OR 97201.
    We offer drain cleaning, pipe repair, and water heater installation.
    Emergencies include burst pipes and major leaks — we route those to our on-call plumber Mike at 503-555-1234.
    Non-emergency calls get scheduled for the next available appointment.
    After hours, callers hear a message and can leave a voicemail.
    """

    # Simulate what extract_memo.py sends
    prompt = f"Extract structured data.\n\nTranscript:\n{sample}"
    result = extract_local(prompt)
    data   = json.loads(result)

    print("\nExtracted:")
    print(f"  company_name  : {data.get('company_name')}")
    print(f"  business_hours: {data.get('business_hours')}")
    print(f"  services      : {data.get('services_supported')}")
    print(f"  emergencies   : {data.get('emergency_definition')}")
    print("\n✅ Local extraction complete!")
