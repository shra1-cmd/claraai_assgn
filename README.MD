# Clara AI Automation Pipeline

A pipeline that converts customer call transcripts into AI voice agent configurations.

## Architecture

dataset/demo_calls/demo{N}.txt -> [extract_memo.py] -> outputs/accounts/acc{N}/v1/
outputs/accounts/acc{N}/v1/ -> [task_tracker.py] -> Asana task created
dataset/onboarding_calls/onboard{N}.txt -> [apply_patch.py] -> outputs/accounts/acc{N}/v2/

## Setup

1. Install Dependencies
   pip install -r requirements.txt

2. Configure Environment
   Create a .env file with the following variables:
   GROQ_API_KEY=your_key
   ASANA_PAT=your_token
   ASANA_PROJECT_GID=your_project_id

3. Add Data(transcripts)
   Place your .txt files in outputs/transcripts/demo_calls/ and outputs/transcripts/demo_calls/onboarding_calls

## Execution

Groq API Pipeline(if u want to execute via groq free tier api key):
python scripts/run_pipeline_groq.py

Local Offline Pipeline(if u want to execute via downloded Hugging face model):
python scripts/run_pipeline_local.py

Dashboard UI:
streamlit run dashboard.py

API Explorer:
uvicorn api.main:app --reload (visit http://localhost:8000/docs)

## Outputs

All outputs go to outputs/accounts/<account_id>/

- v1/memo.json: Extracted account details
- v1/agent_spec.json: Agent prompt configuration
- v2/: Updated details after onboarding
- v2/changes.md: Changelog of what was updated

## n8n Setup

1. Install and run n8n locally.
2. Import the provided workflow JSON.
3. you need to run n8n in root path retel_assignment to allign propery with { ""cmd /c \"set LLM_MODE=local && venv\\Scripts\\python.exe scripts\\run_pipeline.py --file \\\"{{ $json.path }}\\\" 2>&1\ }
4. Two executions will be present 1st one executes pending transcripts,2nd workflow executes new added or any changed txt files(on change detected) in demo_calls,onbording_calls in transcript

## Retell Import

1. Create a Blank Agent in Retell.
2. Open the generated `agent_spec.json` file.
3. Copy the `system_prompt` value and paste it into your Retell agent's prompt settings.
4. Configure a Call Transfer tool using the transfer protocol rules in the JSON.
5. For v2 updates, read `v2/changes.md` and manually adjust the Retell prompt or variables as needed.
