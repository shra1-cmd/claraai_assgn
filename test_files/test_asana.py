import os
import requests
from dotenv import load_dotenv

def create_asana_task(account_name, notes_content):
    # Force a fresh load of the fixed .env
    load_dotenv(override=True)
    
    url = "https://app.asana.com/api/1.0/tasks"
    
    pat = os.getenv("ASANA_PAT")
    project_id = os.getenv("ASANA_PROJECT_GID")
    # This Workspace ID is visible in your GIDs and URL screenshots
    workspace_id = "1213529730277386" 

    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "data": {
            "name": f"AI Follow-up: {account_name}",
            "notes": str(notes_content),
            "projects": [str(project_id)], # Must be a list
            "workspace": workspace_id      # Explicit workspace fixes the 400 error
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print(f"✅ Success: Task created for {account_name}")
        return response.json()['data']['gid']
    else:
        print(f"❌ Asana Error: {response.text}")
        return None

if __name__ == "__main__":
    print("🚀 Starting Final Asana Test...")
    create_asana_task("Verification Task", "Checking fixed .env formatting.")