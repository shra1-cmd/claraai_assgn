import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

# Asana configuration (all IDs sourced from your project URL)
ASANA_TASKS_URL = "https://app.asana.com/api/1.0/tasks"
WORKSPACE_GID   = "1213529730277386"
PROJECT_GID     = os.getenv("ASANA_PROJECT_GID", "1213556771521563")
SECTION_GID     = "1213556771521564"   # "To do" section (verified via API)
PAT             = os.getenv("ASANA_PAT")


def create_asana_task(account_name: str, notes: str) -> str | None:
    """
    Create a follow-up task in the Clara AI Asana project under the 'To do' section.
    Returns the task GID on success, or None if creation fails.
    Failures are non-fatal — the pipeline continues regardless.
    """
    if not PAT:
        print("  Asana PAT not configured — skipping task creation.")
        return None

    headers = {
        "Authorization": f"Bearer {PAT}",
        "Content-Type":  "application/json",
        "Accept":        "application/json"
    }
    payload = {
        "data": {
            "name":      f"AI Follow-up: {account_name}",
            "notes":     str(notes),
            "projects":  [PROJECT_GID],
            "workspace": WORKSPACE_GID,
            "assignee":  "me"
        }
    }

    try:
        response = requests.post(ASANA_TASKS_URL, headers=headers, json=payload, timeout=10)

        if response.status_code == 201:
            task_gid = response.json()["data"]["gid"]
            # Move into the correct section
            requests.post(
                f"https://app.asana.com/api/1.0/sections/{SECTION_GID}/addTask",
                headers={"Authorization": f"Bearer {PAT}", "Content-Type": "application/json"},
                json={"data": {"task": task_gid}},
                timeout=10
            )
            task_url = f"https://app.asana.com/0/{PROJECT_GID}/{task_gid}"
            print(f"  Asana task created for '{account_name}' -> {task_url}")
            return task_gid

        print(f"  Asana: task creation failed ({response.status_code}) — {response.text[:120]}")
        return None

    except requests.exceptions.Timeout:
        print("  Asana: request timed out — skipping.")
        return None
    except Exception as e:
        print(f"  Asana: connection error — {e}")
        return None