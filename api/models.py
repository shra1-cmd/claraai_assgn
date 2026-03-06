"""Pydantic response models for the Clara AI Pipeline API."""
from pydantic import BaseModel
from typing import Any


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_mode: str


class AccountSummary(BaseModel):
    account_id: str
    company_name: str | None
    has_v1: bool
    has_v2: bool


class MemoResponse(BaseModel):
    account_id: str
    version: str
    data: dict[str, Any]


class AgentSpecResponse(BaseModel):
    account_id: str
    version: str
    agent_name: str
    voice_style: str
    data: dict[str, Any]



