
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

server = os.getenv('DB_SERVER')
database = 'PontoEletronicoDB' # Corrected based on screenshot
username = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')

print(f"Connecting to {server}...")

try:
    conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;Connection Timeout=10'
    conn = pyodbc.connect(conn_str)
    print("SUCCESS: Connection established via pyodbc!")
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    row = cursor.fetchone()
    print(f"Server Version: {row[0]}")
    conn.close()
except Exception as e:
    print(f"FAILED pyodbc: {e}")
    try:
        import pymssql
        print("Trying pymssql fallback...")
        conn = pymssql.connect(server=server, user=username, password=password, database=database)
        print("SUCCESS: Connection established via pymssql!")
        conn.close()
    except Exception as e2:
        print(f"FAILED pymssql: {e2}")
