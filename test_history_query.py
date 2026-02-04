import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
sqlite_path = os.getenv('SQLITE_PATH', 'local.db')

def test_query():
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    user_matricula = '171'
    print(f"Testing query for matricula: {user_matricula}")
    
    # Check if records exist at all for this matricula
    cur.execute("SELECT count(*) FROM TimeRecords WHERE matricula = ?", (user_matricula,))
    print(f"Total records for {user_matricula}: {cur.fetchone()[0]}")

    # Check strftime
    cur.execute("SELECT timestamp, strftime('%m', timestamp), strftime('%m', 'now') FROM TimeRecords LIMIT 1")
    res = cur.fetchone()
    if res:
        print(f"Timestamp: {res[0]}, Month: {res[1]}, Now Month: {res[2]}")
    
    # Run full query
    cur.execute("""
        SELECT record_type, timestamp, neighborhood, city 
        FROM TimeRecords 
        WHERE matricula = ? 
          AND strftime('%m', timestamp) = strftime('%m', 'now') 
          AND strftime('%Y', timestamp) = strftime('%Y', 'now')
        ORDER BY timestamp DESC
    """, (user_matricula,))
    rows = cur.fetchall()
    print(f"Query returned {len(rows)} rows.")
    for r in rows:
        print(r)
    conn.close()

if __name__ == "__main__":
    test_query()
