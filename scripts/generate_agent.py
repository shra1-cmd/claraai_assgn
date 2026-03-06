import json
from pathlib import Path
import sys


def _format_hours(hours) -> str:
    """Render business_hours as a readable string regardless of whether it is a dict or string."""
    if isinstance(hours, dict):
        days = ", ".join(hours.get("days", []))
        start = hours.get("start_time", "")
        end = hours.get("end_time", "")
        tz = hours.get("timezone", "")
        return f"{days}, {start}–{end} {tz}".strip()
    return str(hours) if hours else "Monday–Friday, 9:00 AM–5:00 PM"


def generate_agent_spec(memo_path: str, output_path: str) -> None:
    """Generate a Retell-compatible agent spec JSON from an account memo file."""
    with open(memo_path, encoding="utf-8") as f:
        memo = json.load(f)

    company    = memo.get("company_name", "the company")
    hours      = memo.get("business_hours") or {}
    hours_str  = _format_hours(hours)
    address    = memo.get("office_address") or "our main office"
    services   = memo.get("services_supported") or []
    emergency  = memo.get("emergency_definition") or []
    routing    = memo.get("emergency_routing_rules") or "our emergency technician"
    non_emerg  = memo.get("non_emergency_routing_rules") or "collect name and number, schedule appointment"
    transfer_r = memo.get("call_transfer_rules") or "Transfer timeout: 45 seconds. Retry once, then take a message."
    after_hrs  = memo.get("after_hours_flow_summary") or "After-hours calls handled for emergencies only."
    timezone   = hours.get("timezone", "") if isinstance(hours, dict) else ""
    version    = "v1" if "v1" in memo_path else "v2"

    services_str  = "\n".join(f"  - {s}" for s in services)  or "  - General services"
    emergency_str = "\n".join(f"  - {e}" for e in emergency) or "  - Active emergency situation"

    system_prompt = f"""You are a professional, friendly call-handling assistant for {company}.
Greet callers, understand their need, collect only the required information, and route appropriately.
Never mention function calls, tool names, or internal system names to the caller.

---
## BUSINESS INFORMATION
- Company:        {company}
- Address:        {address}
- Business Hours: {hours_str}
- Timezone:       {timezone}
- Services:
{services_str}

---
## OFFICE HOURS CALL FLOW

1. GREET:  "Thank you for calling {company}, this is Clara. How can I help you today?"
2. LISTEN: Let the caller describe their issue fully before responding.
3. TRIAGE: Determine if the issue matches an emergency (see Emergency Definition below).
4. IF EMERGENCY -> follow Emergency Flow.
5. IF NON-EMERGENCY:
   a. Collect caller's full name and best callback number.
   b. Ask only the clarifying questions needed for routing — no extras.
   c. Confirm: "I'll have someone from our team follow up with you shortly."
   d. Ask:    "Is there anything else I can help you with today?"
   e. Close:  "Thank you for calling {company}. Have a great day!"

---
## AFTER-HOURS CALL FLOW

1. GREET:   "Thank you for calling {company}. Our office is currently closed. Our hours are {hours_str}."
2. PURPOSE: "I can assist with emergencies right now. Are you experiencing an urgent situation?"
3. IF NOT EMERGENCY:
   - "I'll note your message and our team will follow up next business day."
   - Collect name and phone number.
   - "Is there anything else?" -> Close.
4. IF EMERGENCY -> follow Emergency Flow.

---
## EMERGENCY DEFINITION
{emergency_str}

---
## EMERGENCY CALL FLOW

1. CONFIRM:  "Just to make sure I connect you with the right person — is this happening right now?"
2. COLLECT (in order):
   a. Caller's full name
   b. Best callback phone number
   c. Address or location of the emergency
3. TRANSFER: "Let me connect you with our emergency team right away. Please hold."
   - Route: {routing}
   - Rules: {transfer_r}
4. IF TRANSFER FAILS:
   - "I wasn't able to connect you live, but your call is marked urgent."
   - "Our team will call you back within 30 minutes."
   - "If there is immediate danger, please call 911."
5. Close: "Is there anything else I can help you with?"

---
## NON-EMERGENCY ROUTING
{non_emerg}

---
## AFTER-HOURS SUMMARY
{after_hrs}

---
## RULES
- Collect only what is needed. For emergencies: name, number, address. For non-emergencies: name and number, plus any routing question required.
- Never say the words "transfer", "function call", "tool", or any system name to the caller.
- If unsure about any detail, say: "Let me have our team follow up with you on that."
- Do not put the caller on hold for more than 45 seconds without checking in.
- Always close with: "Is there anything else I can help you with today?"
"""

    agent_spec = {
        "agent_name": f"{company} AI Assistant",
        "version": version,
        "voice_style": "professional, warm, concise",
        "system_prompt": system_prompt,
        "key_variables": {
            "company_name": company,
            "business_hours": hours,
            "timezone": timezone,
            "office_address": address,
            "services_supported": services,
            "emergency_definition": emergency,
            "emergency_routing_rules": routing
        },
        "tool_invocation_placeholders": {
            "call_transfer":     "Triggered silently on emergency confirmation. Never named to caller.",
            "schedule_callback": "Triggered silently after non-emergency info is collected."
        },
        "call_transfer_protocol": {
            "trigger":            "Emergency confirmed by caller",
            "primary_route":      routing,
            "timeout_and_retry":  transfer_r,
            "transfer_fail_script": "I wasn't able to connect you live, but your call is flagged as urgent. Our team will call you back within 30 minutes."
        },
        "fallback_protocol": {
            "description": "If all transfers fail, collect caller details and commit to a timed callback.",
            "script":      "Our team will call you back within 30 minutes. If there is immediate danger, please call 911."
        }
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(agent_spec, f, indent=2)

    print(f"  Agent spec ({version}) saved -> {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_agent.py <memo_path> <output_path>")
        sys.exit(1)
    generate_agent_spec(sys.argv[1], sys.argv[2])
