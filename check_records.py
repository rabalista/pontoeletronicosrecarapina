import os
from dotenv import load_dotenv
try:
    import pymssql
except ImportError:
    pymssql = None

load_dotenv()
server = os.getenv('DB_SERVER', 'localhost')
database = os.getenv('DB_NAME', 'PontoEletronicoDB')
username = os.getenv('DB_USER', 'sa')
password = os.getenv('DB_PASSWORD', 'MyStrongPass123')

def check():
    print("\n--- SQL Server TimeRecords Count ---")
    if pymssql:
        try:
            conn = pymssql.connect(server=server, user=username, password=password, database=database)
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM TimeRecords")
            count = cur.fetchone()[0]
            print(f"Total rows in TimeRecords: {count}")
            
            if count > 0:
                print("LATEST 5 ROWS:")
                cur.execute("SELECT TOP 5 matricula, record_type, timestamp, neighborhood, city FROM TimeRecords ORDER BY timestamp DESC")
                rows = cur.fetchall()
                for r in rows:
                    print(r)
            conn.close()
        except Exception as e:
            print(f"SQL Server Error: {e}")
    else:
        print("pymssql not installed")

if __name__ == "__main__":
    check()
