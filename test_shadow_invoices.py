import requests
import json
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000/process-invoice/"
INVOICE_FILE = "unlabeled_invoices.json"

def run_shadow_test():
    if not os.path.exists(INVOICE_FILE):
        print(f"ERROR: File not found at {INVOICE_FILE}")
        return

    with open(INVOICE_FILE, "r", encoding="utf-8") as f:
        shadow_data = json.load(f)

    print(f"SHADOW MODE: PROCESSING {len(shadow_data)} UNLABELED INVOICES")
    print("="*70)
    print(f"{'ID':<6} | {'VENDOR':<25} | {'STATUS':<18} | {'MSG'}")
    print("-" * 70)

    success_count = 0

    for inv in shadow_data:
        inv_id = inv.get("invoice_number", "N/A")
        vendor = inv.get("vendor_name", "Unknown")

        try:
            params = {"shadow": "true", "dry_run": "false"}
            
            response = requests.post(
                BASE_URL, 
                params=params, 
                json=inv,
                timeout=30
            )

            if response.status_code == 200:
                res_body = response.json()
                status = res_body.get("status", "???")
                msg = res_body.get("message", "")
                print(f"{inv_id:<6} | {vendor[:25]:<25} | {status:<18} | Processed")
                success_count += 1
            else:
                print(f"{inv_id:<6} | {vendor[:25]:<25} | FAILED ({response.status_code})")
                print(f"   Error Detail: {response.text}")

        except Exception as e:
            print(f"{inv_id:<6} | {vendor[:25]:<25} | CONNECTION ERROR: {str(e)}")

if __name__ == "__main__":
    run_shadow_test()