import os
import time
import json
from dotenv import load_dotenv # Added this
from extract_memo import extract_memo
from generate_agent import generate_agent_spec
from apply_patch import apply_patch
from task_tracker import create_asana_task 

# Ensure environment is loaded at the very start
load_dotenv()

TRANSCRIPTS_DIR = "outputs/transcripts"

def run_pipeline():
    # 1. Setup Directories
    if not os.path.exists(TRANSCRIPTS_DIR):
        print(f"❌ Error: {TRANSCRIPTS_DIR} not found.")
        return

    demo_files = sorted([f for f in os.listdir(TRANSCRIPTS_DIR) if f.startswith("demo")])
    onboard_files = sorted([f for f in os.listdir(TRANSCRIPTS_DIR) if f.startswith("onboard")])

    print(f"🚀 Found {len(demo_files)} demos and {len(onboard_files)} onboarding files.")
    print("-" * 30)

    for i, demo_file in enumerate(demo_files):
        account_id = f"acc{i+1}"
        demo_path = os.path.join(TRANSCRIPTS_DIR, demo_file)
        
        memo_v1_path = f"outputs/accounts/{account_id}/v1/memo.json"
        agent_v1_path = f"outputs/accounts/{account_id}/v1/agent_spec.json"

        print(f"----- Processing {account_id} -----")

        # --- Pipeline A: Demo → v1 agent ---
        print("Creating v1 memo...")
        memo_v1_data = extract_memo(demo_path, memo_v1_path, account_id)
        
        # ASANA INTEGRATION
        # Use .get() safely and ensure we have actual content
        unknowns = memo_v1_data.get("questions_or_unknowns")
        notes = memo_v1_data.get("notes")

        if memo_v1_data and (unknowns or notes):
            print(f"📝 Creating Task Tracker item for {account_id}...")
            # Convert list to string if unknowns is a list
            details_str = json.dumps(unknowns) if isinstance(unknowns, list) else str(unknowns)
            notes_str = str(notes)
            
            combined_details = f"Follow-up needed:\n{details_str}\n\nAdditional Notes:\n{notes_str}"
            
            # CALL ASANA
            create_asana_task(memo_v1_data.get('company_name', account_id), combined_details)

        print("Generating agent v1...")
        generate_agent_spec(memo_v1_path, agent_v1_path)

        # Rate Limit Protection
        print("Waiting 10s for rate limits...")
        time.sleep(10) 

        # --- Pipeline B: Onboarding → v2 update ---
        if i < len(onboard_files):
            onboard_file = onboard_files[i]
            onboard_path = os.path.join(TRANSCRIPTS_DIR, onboard_file)

            print(f"Applying onboarding updates from {onboard_file}...")
            memo_v2_data = apply_patch(memo_v1_path, onboard_path, account_id)

            memo_v2_path = f"outputs/accounts/{account_id}/v2/memo.json"
            agent_v2_path = f"outputs/accounts/{account_id}/v2/agent_spec.json"

            print("Generating agent v2...")
            generate_agent_spec(memo_v2_path, agent_v2_path)
            
            print("Waiting 10s for rate limits...")
            time.sleep(10)

        print(f"✅ Finished {account_id}")
        print()

if __name__ == "__main__":
    run_pipeline()