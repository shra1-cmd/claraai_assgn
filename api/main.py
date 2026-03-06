"""
Clara AI Pipeline — FastAPI Application
Swagger UI: http://localhost:8000/docs

Provides:
  - Read access to all pipeline outputs (memos, agent specs, import guides)
  - Mock Retell API endpoints for integration verification
  - Pipeline trigger endpoint
"""

import json
import os
import uuid
import subprocess
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from api.models import (
    HealthResponse, AccountSummary, MemoResponse, AgentSpecResponse,
    MockRetellAgentRequest, MockRetellAgentResponse, PipelineRunResponse
)

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

OUTPUTS_DIR = Path("outputs/accounts")
LLM_MODE    = os.getenv("LLM_MODE", "groq").lower()
VERSION     = "1.0.0"

# In-memory store for mock Retell agents (resets on server restart)
_mock_retell_agents: dict[str, dict] = {}

app = FastAPI(
    title="Clara AI Pipeline API",
    description=(
        "Mock integration layer for the Clara AI voice agent pipeline.\n\n"
        "Use this to inspect pipeline outputs, trigger runs, and simulate "
        "Retell agent creation — without needing Retell API access.\n\n"
        "**LLM Backend:** `" + LLM_MODE + "` "
        "(`LLM_MODE=groq` for Groq API, `LLM_MODE=local` for flan-t5-base offline)"
    ),
    version=VERSION,
    contact={"name": "Clara AI Pipeline", "url": "https://github.com/shra1-cmd/claraai_assgn"},
    license_info={"name": "MIT"}
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_account_dir(account_id: str) -> Path:
    d = OUTPUTS_DIR / account_id
    if not d.exists():
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found. Run the pipeline first.")
    return d


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path.name}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path.name}")
    return path.read_text(encoding="utf-8")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get(
    "/",
    response_model=HealthResponse,
    summary="Health Check",
    tags=["System"]
)
def health():
    """Returns server status and active LLM mode."""
    return HealthResponse(status="ok", version=VERSION, llm_mode=LLM_MODE)


# ── Accounts ──────────────────────────────────────────────────────────────────

@app.get(
    "/accounts",
    response_model=list[AccountSummary],
    summary="List All Processed Accounts",
    tags=["Accounts"]
)
def list_accounts():
    """Returns all accounts that have been processed by the pipeline."""
    if not OUTPUTS_DIR.exists():
        return []

    accounts = []
    for acc_dir in sorted(OUTPUTS_DIR.iterdir()):
        if not acc_dir.is_dir():
            continue
        memo_v1 = acc_dir / "v1" / "memo.json"
        company = None
        if memo_v1.exists():
            with open(memo_v1, encoding="utf-8") as f:
                company = json.load(f).get("company_name")
        accounts.append(AccountSummary(
            account_id=acc_dir.name,
            company_name=company,
            has_v1=(acc_dir / "v1" / "memo.json").exists(),
            has_v2=(acc_dir / "v2" / "memo.json").exists(),
        ))
    return accounts


@app.get(
    "/accounts/{account_id}/memo/{version}",
    response_model=MemoResponse,
    summary="Get Account Memo",
    tags=["Accounts"]
)
def get_memo(account_id: str, version: str = "v1"):
    """
    Returns the structured account memo for a given account and version (v1 or v2).
    The memo contains all 14 extracted fields: company info, hours, routing rules, etc.
    """
    if version not in ("v1", "v2"):
        raise HTTPException(status_code=400, detail="version must be 'v1' or 'v2'")
    d = _get_account_dir(account_id)
    data = _read_json(d / version / "memo.json")
    return MemoResponse(account_id=account_id, version=version, data=data)


@app.get(
    "/accounts/{account_id}/agent/{version}",
    response_model=AgentSpecResponse,
    summary="Get Agent Spec",
    tags=["Accounts"]
)
def get_agent(account_id: str, version: str = "v1"):
    """
    Returns the full Retell agent spec for a given account and version.
    Includes the complete system prompt, call flows, transfer protocol, and fallback.
    """
    if version not in ("v1", "v2"):
        raise HTTPException(status_code=400, detail="version must be 'v1' or 'v2'")
    d = _get_account_dir(account_id)
    data = _read_json(d / version / "agent_spec.json")
    return AgentSpecResponse(
        account_id=account_id,
        version=version,
        agent_name=data.get("agent_name", ""),
        voice_style=data.get("voice_style", ""),
        data=data
    )


@app.get(
    "/accounts/{account_id}/import-guide/{version}",
    response_class=PlainTextResponse,
    summary="Get Retell Manual Import Guide",
    tags=["Accounts"]
)
def get_import_guide(account_id: str, version: str = "v1"):
    """
    Returns the pre-filled Retell manual import guide (Markdown) for an account.
    Use this to recreate the agent in the Retell UI step-by-step.
    """
    if version not in ("v1", "v2"):
        raise HTTPException(status_code=400, detail="version must be 'v1' or 'v2'")
    d = _get_account_dir(account_id)
    return _read_text(d / version / "retell_import_guide.md")


@app.get(
    "/accounts/{account_id}/changelog",
    response_class=PlainTextResponse,
    summary="Get v1→v2 Changelog",
    tags=["Accounts"]
)
def get_changelog(account_id: str):
    """Returns the field-level changelog from v1 to v2 for an account."""
    d = _get_account_dir(account_id)
    return _read_text(d / "v2" / "changes.md")


# ── Pipeline ──────────────────────────────────────────────────────────────────

@app.post(
    "/pipeline/run",
    response_model=PipelineRunResponse,
    summary="Trigger Full Pipeline",
    tags=["Pipeline"]
)
def run_pipeline():
    """
    Triggers a full pipeline run in the background (non-blocking).
    The pipeline will process all transcripts in outputs/transcripts/
    and regenerate all account outputs.

    Note: The pipeline runs asynchronously. Check the server logs for progress.
    """
    try:
        python = sys.executable
        subprocess.Popen(
            [python, "scripts/run_pipeline.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return PipelineRunResponse(
            status="started",
            message="Pipeline is running in the background. Check server logs for progress."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {e}")


# ── Mock Retell API ───────────────────────────────────────────────────────────

@app.post(
    "/retell/agent",
    response_model=MockRetellAgentResponse,
    summary="Mock: Create Retell Agent",
    tags=["Mock Retell API"]
)
def mock_create_agent(request: MockRetellAgentRequest):
    """
    **Mock endpoint** simulating `POST https://api.retellai.com/v2/create-agent`.

    Accepts an agent spec and returns a synthetic agent_id.
    Use this to verify the agent spec structure before going live with Retell.

    In production, replace this with a real Retell API call using your API key.
    """
    agent_id = f"mock-agent-{str(uuid.uuid4())[:8]}"
    _mock_retell_agents[agent_id] = {
        "agent_id":   agent_id,
        "agent_name": request.agent_name,
        "version":    request.version,
        "voice_style": request.voice_style,
        "prompt_length": len(request.system_prompt),
    }
    return MockRetellAgentResponse(
        agent_id=agent_id,
        agent_name=request.agent_name,
        status="created",
        voice_id="11labs-rachel",
        language="en-US",
        webhook_url=None,
        note=(
            "This is a MOCK response. The agent was not created in Retell. "
            "To create a real agent, use your Retell API key and follow RETELL_SETUP.md."
        )
    )


@app.get(
    "/retell/agents",
    summary="Mock: List All Retell Agents",
    tags=["Mock Retell API"]
)
def mock_list_agents():
    """
    **Mock endpoint** simulating `GET https://api.retellai.com/v2/list-agents`.

    Returns all agents created via `POST /retell/agent` in this session.
    Also includes agents derived from pipeline outputs (read from disk).
    """
    # Agents created via mock API in this session
    session_agents = list(_mock_retell_agents.values())

    # Agents derived from pipeline outputs
    disk_agents = []
    if OUTPUTS_DIR.exists():
        for acc_dir in sorted(OUTPUTS_DIR.iterdir()):
            if not acc_dir.is_dir():
                continue
            for version in ("v1", "v2"):
                spec_path = acc_dir / version / "agent_spec.json"
                if spec_path.exists():
                    with open(spec_path, encoding="utf-8") as f:
                        spec = json.load(f)
                    disk_agents.append({
                        "source":     "pipeline_output",
                        "account_id": acc_dir.name,
                        "version":    version,
                        "agent_name": spec.get("agent_name"),
                        "voice_style": spec.get("voice_style"),
                    })

    return {
        "mock_session_agents": session_agents,
        "pipeline_output_agents": disk_agents,
        "total": len(session_agents) + len(disk_agents)
    }
