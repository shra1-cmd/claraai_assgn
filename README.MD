Clara AI Automation Pipeline

This project implements a zero-cost automation pipeline that converts customer call transcripts into AI voice agent configurations.

The system automatically:

Generates a preliminary Retell agent configuration from a demo call.

Applies onboarding updates to refine the agent.

Produces versioned agent specs (v1 → v2) with change tracking.

Architecture
Demo Call Transcript
↓
LLM Extraction (Groq)
↓
Account Memo JSON
↓
Retell Agent Spec v1
↓
Onboarding Transcript
↓
Update Extraction
↓
Memo Patch
↓
Retell Agent Spec v2
↓
Changelog

The workflow is orchestrated using LangGraph.

Tech Stack
Layer Tool
Orchestration LangGraph
LLM Groq (LLaMA-3)
Storage Local JSON
Transcription Whisper (optional)
Agent Config Retell Agent Spec JSON
Running the Pipeline

Install dependencies:

pip install -r requirements.txt

Run the pipeline:

python scripts/pipeline_graph.py

The system will process all demo and onboarding transcripts automatically.

Output Structure
outputs/

accounts/

acc1/
v1/
memo.json
agent_spec.json

v2/
memo.json
agent_spec.json
changes.md

Each account includes:

Initial agent configuration (v1)

Updated agent configuration (v2)

Change log

Retell Integration

This project generates a Retell Agent Draft Spec JSON that mirrors the configuration used when creating a Retell voice agent.

If using the Retell dashboard manually:

Create a new agent

Copy the generated system_prompt

Configure variables from key_variables

Apply transfer rules from call_transfer_protocol

Zero-Cost Constraint

The pipeline runs entirely on free-tier tools:

Groq free API

Local Python scripts

JSON storage

No paid services are required.
