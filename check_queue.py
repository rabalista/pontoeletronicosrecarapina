import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
sqlite_path = os.getenv('SQLITE_PATH', 'local.db')

def check_queue():
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    print("--- OfflineQueue Records ---")
    cur.execute("SELECT * FROM OfflineQueue ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    for r in rows:
        print(r)
    conn.close()

if __name__ == "__main__":
    check_queue()
