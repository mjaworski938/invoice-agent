import json
import requests
import time
import os

from dotenv import load_dotenv
load_dotenv()

BASE_URL = "http://127.0.0.1:8000"

def run_tests():

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    test_cases_path = os.path.join(BASE_DIR, "test_cases.json")
    GLOBAL_DRY_RUN = os.getenv("GLOBAL_DRY_RUN", "false").lower() == "true"

    # 1. Load your 6 cases
    with open(test_cases_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    print(f"Starting Invoice Processing Test for {len(test_cases)} cases...\n")

    for i, case in enumerate(test_cases, 1):
        print(f"--- Case {i}: {case.get('vendor_name')} ---")
        
        try:
            response = requests.post(
                f"{BASE_URL}/process-invoice/?dry_run={GLOBAL_DRY_RUN}",
                json=case
            )

            resp_data = response.json()

            if GLOBAL_DRY_RUN == True:
                print(f"DRY RUN MODE: No changes made to Database.")
                
                # Flagged cases do not have data for AI output
                if resp_data.get('data'):
                    print(f"PROPOSED ENTRIES: {resp_data['data']['line_items']}")
                else:
                    print(f"PROPOSED ENTRIES: None (Invoice was FLAGGED)")

            if response.status_code == 200:
                data = response.json()
                print(f"Result: {data['status']}")
                print(f"Message: {data['message']}")
            else:
                print(f"Error {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"Connection failed: {e}")

if __name__ == "__main__":
    run_tests()