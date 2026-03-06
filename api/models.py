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


class MockRetellAgentRequest(BaseModel):
    agent_name: str
    system_prompt: str
    voice_style: str = "professional, warm, concise"
    version: str = "v1"

    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "BlueSky Electrical AI Assistant",
                "system_prompt": "You are a professional call-handling assistant for BlueSky Electrical...",
                "voice_style": "professional, warm, concise",
                "version": "v2"
            }
        }


class MockRetellAgentResponse(BaseModel):
    agent_id: str
    agent_name: str
    status: str
    voice_id: str
    language: str
    webhook_url: str | None
    note: str


class PipelineRunResponse(BaseModel):
    status: str
    message: str
