import json
import os
from dotenv import load_dotenv
from groq import Groq, RateLimitError
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PROMPT = """
You are an expert business analyst and information extraction system.
Return ONLY a valid JSON object. 

Fields to extract:
- account_id: (Keep null if not in transcript)
- company_name: Official name of the business.
- business_hours: Detailed hours of operation.
- office_address: Full physical address.
- services_supported: List of services the company provides.
- emergency_definition: A python list of scenarios that constitute an "emergency".
- emergency_routing_rules: How calls are handled during emergencies.
- non_emergency_routing_rules: How standard calls are handled.
- call_transfer_rules: Specific logic for transfers (timeouts, retries, and phrases).
- integration_constraints: Technical or software limitations mentioned.
- after_hours_flow_summary: Summary of calls when office is closed.
- office_hours_flow_summary: Summary of calls during standard hours.
- questions_or_unknowns: List of items requiring follow-up.
- notes: Additional context.

Transcript:
{transcript}
"""

@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5)
)
def call_groq_api(prompt):
    return client.chat.completions.create(
        model="llama-3.3-70b-versatile", # Verified Free Model
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"}
    )

def extract_memo(transcript_path, output_path, account_id):
    with open(transcript_path) as f:
        transcript = f.read()

    print(f"🔍 Extracting Memo V1 for {account_id}...")
    response = call_groq_api(PROMPT.format(transcript=transcript))
    text = response.choices[0].message.content

    try:
        memo = json.loads(text)
    except:
        memo = {"error": "JSON parsing failed", "raw": text}

    memo["account_id"] = account_id
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(memo, f, indent=2)

    print("✅ Memo saved:", output_path)
    return memo # Crucial for run_pipeline.py