import sqlite3
from tabulate import tabulate

import os

from dotenv import load_dotenv
load_dotenv()

def query_db():
    conn = sqlite3.connect(os.getenv("DATABASE_URL")[12:])
    cursor = conn.cursor()

    print("DATABASE VIEWER")

    print("\n--- TABLE: journal_entries ---")
    cursor.execute("SELECT id, invoice_number, vendor_name, total_amount, status FROM journal_entries")
    headers = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    
    if rows:
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        print("Empty Table.")

    
    print("\n--- TABLE: journal_line_items ---")
    cursor.execute("SELECT id, parent_id, gl_code, description, amount FROM journal_line_items")
    headers = [description[0] for description in cursor.description]
    rows = cursor.fetchall()

    if rows:
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        print("Empty Table.")

    conn.close()

if __name__ == "__main__":
    try:
        query_db()
    except Exception as e:
        print(f"❌ Error reading database: {e}")