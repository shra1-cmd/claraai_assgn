# Clara AI Automation Pipeline

A zero-cost, end-to-end automation pipeline that converts customer call transcripts into versioned AI voice agent configurations for Retell.

---

## Architecture & Data Flow

```
dataset/demo_calls/demo{N}.txt
        ↓
[ extract_memo.py ] — LLM extraction via Groq (llama-3.3-70b-versatile)
        ↓
outputs/accounts/acc{N}/v1/memo.json   (Account Memo JSON)
        ↓
[ generate_agent.py ] — Template-based prompt builder
        ↓
outputs/accounts/acc{N}/v1/agent_spec.json   (Retell Agent Draft Spec v1)
        ↓
[ task_tracker.py ] — Creates Asana task for flagged unknowns
        ↓
dataset/onboarding_calls/onboard{N}.txt
        ↓
[ apply_patch.py ] — LLM diff extraction via Groq
        ↓
outputs/accounts/acc{N}/v2/memo.json + changes.md   (updated memo + changelog)
        ↓
[ generate_agent.py ] — Rebuilt prompt
        ↓
outputs/accounts/acc{N}/v2/agent_spec.json   (Retell Agent Draft Spec v2)
```

Orchestrated via **LangGraph** (`scripts/pipeline_graph.py`) or directly via `scripts/run_pipeline.py`.

---

## Tech Stack

| Layer         | Tool                                             |
| ------------- | ------------------------------------------------ |
| Orchestration | LangGraph + Python                               |
| LLM           | Groq API — `llama-3.3-70b-versatile` (free tier) |
| Storage       | Local JSON files                                 |
| Transcription | OpenAI Whisper (local, optional)                 |
| Task Tracking | Asana API (free tier)                            |
| Agent Config  | Retell Agent Spec JSON                           |
| Automation UI | n8n (self-hosted via Docker)                     |

---

## Setup Instructions

### 1. Clone and Install

```bash
git clone https://github.com/shra1-cmd/claraai_assgn.git
cd claraai_assgn
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root (never commit this):

```env
GROQ_API_KEY=your_groq_api_key_here
ASANA_PAT=your_asana_personal_access_token
ASANA_PROJECT_GID=your_asana_project_id
```

**How to get these:**

- **Groq API Key:** [console.groq.com](https://console.groq.com) → API Keys → Create Key (free)
- **Asana PAT:** Asana → Profile Settings → Apps → Personal Access Tokens
- **Asana Project GID:** Open your Asana project in browser → the number in the URL

### 3. Add Your Dataset

Place transcript `.txt` files in:

```
dataset/
  demo_calls/      ← one file per demo call (demo1.txt, demo2.txt ...)
  onboarding_calls/ ← one file per onboarding call (onboard1.txt ...)
```

The pipeline pairs files by sort order: `demo1.txt` → `onboard1.txt`, etc.

### 4. Run the Pipeline

```bash
cd scripts
python run_pipeline.py
```

This processes all accounts end-to-end automatically.

---

## Output Structure

```
outputs/
  accounts/
    acc1/
      v1/
        memo.json          ← extracted account memo
        agent_spec.json    ← Retell agent draft (v1)
      v2/
        memo.json          ← updated memo after onboarding
        agent_spec.json    ← updated agent spec (v2)
        changes.md         ← changelog: what changed and why
    acc2/ ...
    acc3/ ...
```

---

## Retell Integration

This project generates a **Retell Agent Draft Spec JSON** — a structured file matching Retell's agent configuration format.

### Using the Retell Dashboard (Manual Import)

1. Go to [app.retell.ai](https://app.retell.ai) and create a new agent
2. Open `outputs/accounts/acc{N}/v1/agent_spec.json`
3. Copy the value of `system_prompt` → paste into the agent's system prompt field
4. Configure variables from `key_variables` (business hours, timezone, address, etc.)
5. Apply transfer rules from `call_transfer_protocol`
6. For v2, repeat using the files in the `v2/` folder

### Programmatic API (if available on your Retell tier)

The `agent_spec.json` mirrors the Retell API body. You can POST it directly:

```bash
curl -X POST https://api.retellai.com/v2/create-agent \
  -H "Authorization: Bearer YOUR_RETELL_KEY" \
  -d @outputs/accounts/acc1/v1/agent_spec.json
```

---

## n8n Workflow Setup (Optional)

The pipeline can be triggered via n8n for visual scheduling and monitoring.

### Quick Start (Docker)

```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

Then:

1. Open [http://localhost:5678](http://localhost:5678)
2. Go to **Workflows → Import from File**
3. Upload `workflows/n8n_workflow.json`
4. Set env variables in n8n: `GROQ_API_KEY`, `ASANA_PAT`
5. Click **Execute Workflow**

---

## Known Limitations

- **Transcript quality dependency:** Extraction quality directly depends on transcript richness. Very short or low-detail transcripts will produce memos with many `null` fields.
- **Groq rate limits:** Free tier has per-minute token limits. The pipeline includes `time.sleep(10)` between accounts and uses `tenacity` retry logic, but very large batches may still hit limits.
- **No idempotency lock:** Running the pipeline twice overwrites existing outputs silently. Add a hash check or output version check for production use.
- **Asana is optional:** If `ASANA_PAT` is not set, Asana task creation will fail gracefully but the rest of the pipeline continues.
- **Whisper transcription is separate:** `scripts/transcribe.py` handles audio → text conversion but is not integrated into the main pipeline run. Call it manually per file: `python scripts/transcribe.py audio.mp3 output.txt`

---

## What I Would Improve With Production Access

- **Retell API integration:** With a paid Retell tier, the pipeline would auto-create and update agents programmatically rather than requiring manual UI import.
- **Real-time webhook trigger:** Replace manual trigger with a webhook from your CRM or calendar tool to kick off Pipeline A automatically after a demo call is logged.
- **Vector search on memos:** Index all account memos in a vector store (e.g. Supabase pgvector) to enable semantic lookup across accounts.
- **Structured output validation:** Add JSON Schema validation after LLM extraction to reject and retry malformed outputs instead of writing error objects to disk.
- **UI dashboard:** A simple web dashboard to view all accounts, compare v1 vs v2 diffs, and trigger re-runs per account.
- **Parallel processing:** Replace sequential `time.sleep` with async LLM calls and proper rate-limit-aware batching for faster throughput.
