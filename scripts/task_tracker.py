import os
import requests
from dotenv import load_dotenv

def create_asana_task(account_name, notes_content):
    """
    Creates a task in Asana. 
    Explicitly includes Workspace and Project IDs to prevent the 400 error.
    """
    # Reload environment variables to ensure we have the latest from .env
    load_dotenv(override=True)
    
    url = "https://app.asana.com/api/1.0/tasks"
    
    pat = os.getenv("ASANA_PAT")
    project_id = os.getenv("ASANA_PROJECT_GID")
    
    # This is your Workspace ID extracted from your previous screenshots
    # Adding this explicitly fixes the "specify one of workspace, parent, projects" error.
    workspace_id = "1213529730277386" 

    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }
    
    # Constructing the payload
    # Asana API requires 'projects' to be an array of strings.
    payload = {
        "data": {
            "name": f"AI Follow-up: {account_name}",
            "notes": str(notes_content),
            "projects": [str(project_id)], 
            "workspace": str(workspace_id),
            "assignee": "me" 
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            task_gid = response.json()['data']['gid']
            print(f"✅ Success: Task created for {account_name} (GID: {task_gid})")
            return task_gid
        else:
            # Detailed error reporting to help us if it fails again
            print(f"❌ Failed to create task for {account_name}")
            print(f"❌ Status Code: {response.status_code}")
            print(f"❌ Error Detail: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {str(e)}")
        return None

# The "main" block for standalone testing
if __name__ == "__main__":
    print("🚀 Running Standalone Asana Connection Test...")
    
    # Test Data
    test_account = "Acc1_Test_Run"
    test_notes = "This is a test to verify the fixed workspace/project logic."
    
    # Verification of environment variables before calling
    if not os.getenv("ASANA_PAT"):
        print("❌ Error: ASANA_PAT is missing from your .env file.")
    elif not os.getenv("ASANA_PROJECT_GID"):
        print("❌ Error: ASANA_PROJECT_GID is missing from your .env file.")
    else:
        create_asana_task(test_account, test_notes)