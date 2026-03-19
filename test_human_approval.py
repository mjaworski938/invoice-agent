import requests
import sqlite3
from tabulate import tabulate
import os

from dotenv import load_dotenv
load_dotenv()

# Configuration
BASE_URL = "http://127.0.0.1:8000"

def get_pending_queue():
    """Fetches everything that isn't POSTED yet."""
    conn = sqlite3.connect(os.getenv("DATABASE_URL")[12:])
    cursor = conn.cursor()
    query = """
    SELECT id, invoice_number, vendor_name, total_amount, status 
    FROM journal_entries 
    WHERE status IN ('SHADOW_PROPOSAL', 'PENDING_APPROVAL')
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows

def approve_invoice(invoice_number):
    """Hits the FastAPI endpoint to promote the invoice."""
    try:
        url = f"{BASE_URL}/approve-invoice/{invoice_number}"
        response = requests.post(url)
        if response.status_code == 200:
            print(f"API SUCCESS: {invoice_number} is now POSTED.")
            return True
        else:
            print(f"API ERROR: {response.json().get('detail')}")
            return False
    except Exception as e:
        print(f"CONNECTION FAILURE: {e}")
        return False

def run_loop():
    print("\n" + "STARTING HUMAN-IN-THE-LOOP REVIEW SESSION")
    
    while True:
        queue = get_pending_queue()
        
        if not queue:
            print("Invoice Processing Completed")
            break
            
        print(f"PENDING REVIEW for ({len(queue)} items)")
        # We display the ID, but we need the Invoice # for the API call
        print(tabulate(queue, headers=["ID", "Invoice #", "Vendor", "Amount", "Status"], tablefmt="fancy_grid"))
        
        user_input = input("\nEnter the ID to Approve (or 'q' to quit): ").strip()
        
        if user_input.lower() == 'q':
            break
            
        # --- THE FIX ---
        # Find the row where the ID matches the user's input
        # row[0] is the ID, row[1] is the Invoice Number
        selected_row = next((row for row in queue if str(row[0]) == user_input), None)
        
        if selected_row:
            invoice_num = selected_row[1] # Extract 'UL-5'
            approve_invoice(invoice_num)   # Send 'UL-5' to the API
        else:
            print(f"Error: ID '{user_input}' is not in the list.")

if __name__ == "__main__":
    run_loop()