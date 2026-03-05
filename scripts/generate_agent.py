import json
from pathlib import Path
import sys


def generate_agent_spec(memo_path, output_path):

    with open(memo_path) as f:
        memo = json.load(f)

    company = memo.get("company_name", "Service Company")
    hours = memo.get("business_hours", "unknown hours")
    emergency = memo.get("emergency_definition", [])
    services = memo.get("services_supported", [])

    version = "v1" if "v1" in memo_path else "v2"

    system_prompt = f"""
You are a professional call assistant for {company}.

Business hours: {hours}

Services:
{services}

Emergency cases:
{emergency}
"""

    agent_spec = {
        "agent_name": f"{company} AI Assistant",
        "version": version,
        "voice_style": "professional",
        "system_prompt": system_prompt,
        "key_variables": {
            "business_hours": hours,
            "services": services,
            "emergency_definition": emergency
        },
        "call_transfer_protocol": memo.get("emergency_routing_rules"),
        "fallback_protocol": "If transfer fails reassure caller and promise follow-up"
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(agent_spec, f, indent=2)

    print("Agent spec created:", output_path)


if __name__ == "__main__":

    memo_path = sys.argv[1]
    output_path = sys.argv[2]

    generate_agent_spec(memo_path, output_path)