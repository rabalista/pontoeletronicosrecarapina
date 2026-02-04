import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
sqlite_path = os.getenv('SQLITE_PATH', 'local.db')

def check_schema():
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    print("--- TimeRecords Schema ---")
    cur.execute("PRAGMA table_info(TimeRecords)")
    for col in cur.fetchall():
        print(col)
    
    print("\n--- Last Record ---")
    cur.execute("SELECT * FROM TimeRecords ORDER BY id DESC LIMIT 1")
    print(cur.fetchone())
    conn.close()

if __name__ == "__main__":
    check_schema()
