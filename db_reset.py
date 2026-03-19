import sqlite3
import os
from dotenv import load_dotenv
load_dotenv()

def reset_db():
    # 1. Open connection
    conn = sqlite3.connect(os.getenv("DATABASE_URL")[12:])
    cursor = conn.cursor()

    print("DATABASE RESET: CLEARING ALL TABLES")

    try:
        cursor.execute("DELETE FROM journal_line_items")
        cursor.execute("DELETE FROM journal_entries")
        conn.commit() 
        print("✅ Data cleared and committed.")

        
        conn.isolation_level = None 
        cursor.execute("VACUUM")
        conn.isolation_level = "" 
        
        print("ids reset with vacuum")
        print("All tables in DB are now empty")

    except Exception as e:
        print(f"DB Reset has Failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    confirm = input("Confirm WIPE all data? (y/n): ").strip().lower()
    if confirm == 'y':
        reset_db()
    else:
        print("Reset cancelled.")