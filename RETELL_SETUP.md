# Retell Agent Setup Guide

This guide explains how to manually create a Retell voice agent from a generated `agent_spec.json`.

Use this when:

- You are on Retell's free tier and programmatic API access is not available
- You want to verify or fine-tune the agent in the UI before going live

For a pre-filled, account-specific checklist, see `retell_import_guide.md` inside each account's `v1/` or `v2/` folder.

---

## Prerequisites

1. Create a free Retell account at [app.retellai.com](https://app.retellai.com)
2. Open the generated `agent_spec.json` for your account (e.g. `outputs/accounts/acc1/v1/agent_spec.json`)

---

## Step-by-Step: Create the Agent in Retell UI

### Step 1 — Create a New Agent

1. Log in to [app.retellai.com](https://app.retellai.com)
2. Click **"Create Agent"** in the top right
3. Select **"Blank Agent"** (not from template)

---

### Step 2 — Set Agent Name

- **Field:** Agent Name
- **Value:** Copy from `agent_spec.json` → `agent_name`
- **Example:** `BlueSky Electrical AI Assistant`

---

### Step 3 — Set the LLM / Model

- **Field:** LLM Provider
- **Recommended:** Select **Retell LLM** or any free option available on your tier
- If using OpenAI: select `GPT-4o` or `GPT-4o mini` (requires OpenAI API key)
- If using local/free: select `Llama 3` via Groq (requires Groq API key)

---

### Step 4 — Paste the System Prompt

This is the most important step.

1. In the agent editor, find the **"System Prompt"** or **"Agent Prompt"** field
2. Open your `agent_spec.json` and copy the entire value of `"system_prompt"`
3. Paste it into the field

> The system prompt already contains:
>
> - Office hours call flow (greet → triage → route → close)
> - After-hours call flow
> - Emergency definition and call flow
> - Transfer-fail fallback script
> - Strict hygiene rules (no jargon to caller, no over-questioning)

---

### Step 5 — Set the Greeting Message

1. Find the **"Greeting Message"** or **"First Message"** field
2. Enter:

```
Thank you for calling [Company Name], this is Clara. How can I help you today?
```

Replace `[Company Name]` with the value from `agent_spec.json` → `key_variables.company_name`

---

### Step 6 — Select a Voice

| Voice Style                 | Recommended Voice                                  |
| --------------------------- | -------------------------------------------------- |
| Professional, warm, concise | **ElevenLabs — Rachel** or **Play.ht — Jennifer**  |
| Neutral / formal            | **Azure — Jenny Neural**                           |
| Any free option             | Use Retell's default voice if no API key available |

The required style is in `agent_spec.json` → `voice_style`: `"professional, warm, concise"`

---

### Step 7 — Configure Call Transfer (Emergency Routing)

1. In the agent editor, find **"Tools"** or **"Functions"**
2. Add a **Call Transfer** tool
3. Configure it using values from `agent_spec.json` → `call_transfer_protocol`:

| Field                | Value from JSON                               |
| -------------------- | --------------------------------------------- |
| Trigger condition    | `call_transfer_protocol.trigger`              |
| Transfer destination | `call_transfer_protocol.primary_route`        |
| Timeout              | `call_transfer_protocol.timeout_and_retry`    |
| Failure script       | `call_transfer_protocol.transfer_fail_script` |

> **Important:** Name the tool something neutral in the UI (e.g. `connect_emergency`).
> The system prompt already instructs the agent to never say the tool name to the caller.

---

### Step 8 — Set Key Variables (Optional but Recommended)

If Retell supports custom variables, add these from `agent_spec.json` → `key_variables`:

| Variable                  | Value                            |
| ------------------------- | -------------------------------- |
| `company_name`            | Company name string              |
| `business_hours`          | Hours object or formatted string |
| `timezone`                | e.g. `Central Time`              |
| `office_address`          | Full address string              |
| `emergency_definition`    | List of emergency scenarios      |
| `emergency_routing_rules` | Transfer routing instructions    |

---

### Step 9 — Configure Fallback (Transfer Fail)

1. Find **"Fallback Behavior"** in the agent settings
2. Set the fallback script from `agent_spec.json` → `fallback_protocol.script`:

```
Our team will call you back within 30 minutes.
If there is immediate danger, please call 911.
```

---

### Step 10 — Test the Agent

1. Click **"Test Agent"** or **"Call Agent"** in the Retell dashboard
2. Test these scenarios:
   - Call during "business hours" — agent should greet and offer routing
   - Say an emergency keyword (e.g. "burst pipe", "power outage") — agent should confirm and transfer
   - Say a non-emergency need — agent should collect name + number, promise follow-up
   - Simulate transfer failure — agent should deliver fallback script

---

### Step 11 — Publish / Deploy

1. Click **"Publish Agent"** or **"Deploy"**
2. Note the **Agent ID** shown — save it if you want to use the Retell API later
3. For webhook integration, set a webhook URL under **Settings → Webhook**

---

## Updating from v1 to v2

When onboarding updates arrive:

1. Open `outputs/accounts/<account_id>/v2/agent_spec.json`
2. Open `outputs/accounts/<account_id>/v2/changes.md` to see what changed
3. In the Retell UI, find your existing agent and click **Edit**
4. Update only the fields listed in `changes.md`
5. Re-publish the agent

---

## Retell API (If Available on Your Tier)

If your Retell plan allows API access, you can create the agent programmatically:

```bash
curl -X POST https://api.retellai.com/v2/create-agent \
  -H "Authorization: Bearer YOUR_RETELL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "BlueSky Electrical AI Assistant",
    "response_engine": {
      "type": "retell-llm",
      "llm_id": "YOUR_LLM_ID"
    },
    "voice_id": "YOUR_VOICE_ID",
    "language": "en-US"
  }'
```

Then update the LLM system prompt via:

```bash
curl -X PATCH https://api.retellai.com/v2/update-retell-llm/YOUR_LLM_ID \
  -H "Authorization: Bearer YOUR_RETELL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "general_prompt": "<paste system_prompt value here>"
  }'
```

> See [Retell API Docs](https://docs.retellai.com/api-references/agent/create-agent) for full reference.

---

## File Reference

| File                                              | Purpose                                     |
| ------------------------------------------------- | ------------------------------------------- |
| `outputs/accounts/accN/v1/agent_spec.json`        | Full agent spec — v1 (post demo call)       |
| `outputs/accounts/accN/v2/agent_spec.json`        | Updated agent spec — v2 (post onboarding)   |
| `outputs/accounts/accN/v1/retell_import_guide.md` | Pre-filled step-by-step import guide for v1 |
| `outputs/accounts/accN/v2/retell_import_guide.md` | Pre-filled step-by-step import guide for v2 |
| `outputs/accounts/accN/v2/changes.md`             | What changed from v1 → v2 and why           |
