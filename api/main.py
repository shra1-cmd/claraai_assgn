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
    HealthResponse, AccountSummary, MemoResponse, AgentSpecResponse
)

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

OUTPUTS_DIR = Path("outputs/accounts")
LLM_MODE    = os.getenv("LLM_MODE", "groq").lower()
VERSION     = "1.0.0"

app = FastAPI(
    title="Clara AI Pipeline API",
    description="Minimal API to inspect generated account memos and agent specs.",
    version=VERSION,
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


# End of file
