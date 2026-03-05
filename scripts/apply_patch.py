import json
import os
from dotenv import load_dotenv
from pathlib import Path
from groq import Groq, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PATCH_PROMPT = """
You are an update extraction system.
Compare the onboarding transcript against the previous memo.
Extract ONLY the fields that have changed or were previously null.
Return valid JSON containing ONLY these updated fields.

Previous Memo:
{memo}

Onboarding Transcript:
{transcript}
"""

@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5)
)
def extract_updates(transcript, memo):
    prompt = PATCH_PROMPT.format(
        transcript=transcript,
        memo=json.dumps(memo, indent=2)
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def apply_patch(v1_path, transcript_path, account_id):
    with open(v1_path) as f:
        memo = json.load(f)
    with open(transcript_path) as f:
        transcript = f.read()

    print(f"🩹 Applying updates for {account_id}...")
    updates = extract_updates(transcript, memo)
    
    updated_memo = memo.copy()
    updated_memo.update(updates)

    # Save Memo V2
    v2_dir = f"outputs/accounts/{account_id}/v2"
    Path(v2_dir).mkdir(parents=True, exist_ok=True)
    v2_memo_path = f"{v2_dir}/memo.json"
    with open(v2_memo_path, "w") as f:
        json.dump(updated_memo, f, indent=2)

    # Generate Changelog
    changes = [f"{k}: {memo.get(k)} → {v}" for k, v in updates.items()]
    with open(f"{v2_dir}/changes.md", "w", encoding="utf-8") as f:
        f.write(f"# Updates for {account_id}\n" + "\n".join(changes))

    print("✅ Memo v2 and Changelog created.")
    return updated_memo # Crucial for run_pipeline.py