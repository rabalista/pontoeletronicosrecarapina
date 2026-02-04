from flask import Flask, request, jsonify, send_from_directory, render_template, send_file
from flask_cors import CORS
import os
import bcrypt
import jwt
import datetime
import pytz
import sys
import time
import threading
from functools import wraps

import sqlite3
from dotenv import load_dotenv
import openpyxl
from io import BytesIO

try:
    import pymssql
except ImportError:
    pymssql = None

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
_secret = os.getenv('SECRET_KEY')
if not _secret:
    _secret = os.getenv('DB_PASSWORD', 'ponto_sre_carapina')
app.config['SECRET_KEY'] = _secret

# Allow all origins, all methods, and specifically allow our bypass headers
try:
    CORS(app, resources={r"/api/*": {"origins": "*"}}, allow_headers=["*", "Authorization", "Content-Type", "Bypass-Tunnel-Reminder", "X-Tunnel-Skip-Proxy-Warning"], methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"])
except:
    pass

# Database Configuration
server = os.getenv('DB_SERVER')
database = os.getenv('DB_NAME')
username = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
sqlite_path = os.getenv('SQLITE_PATH', 'local.db')
USE_SQLITE = os.getenv('USE_SQLITE', 'true').lower() == 'true'

# Optional: initialize database/tables on startup when deploying
if os.getenv('INIT_DB_ON_START', 'false').lower() == 'true':
    try:
        from setup_db import create_database, create_tables
        create_database()
        create_tables()
    except Exception:
        pass

# Global DB Status
DB_ONLINE = False

# Configuração SQL Server
db_server = os.getenv('DB_SERVER')
db_name = os.getenv('DB_NAME')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')

# Global Sync Locking
SYNC_LOCKS = {}
SYNC_LOCKS_LOCK = threading.Lock()

def get_user_sync_lock(matricula):
    with SYNC_LOCKS_LOCK:
        if matricula not in SYNC_LOCKS:
            SYNC_LOCKS[matricula] = threading.Lock()
        return SYNC_LOCKS[matricula]

def get_remote_db_connection():
    """Explicitly tries to connect to SQL Server, ignoring USE_SQLITE."""
    try:
        import pyodbc
        conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={db_server};DATABASE={db_name};UID={db_user};PWD={db_password};TrustServerCertificate=yes;Connection Timeout=5'
        conn = pyodbc.connect(conn_str)
        conn.autocommit = True
        return conn
    except Exception:
        try:
            import pymssql
            conn = pymssql.connect(server=db_server, user=db_user, password=db_password, database=db_name, timeout=5, as_dict=True, autocommit=True)
            return conn
        except Exception:
            return None

def get_db_connection():
    if USE_SQLITE:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        ensure_sqlite_schema(conn)
        return conn
    
    # Try SQL Server
    try:
        import pyodbc
        conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={db_server};DATABASE={db_name};UID={db_user};PWD={db_password};TrustServerCertificate=yes;Connection Timeout=5'
        conn = pyodbc.connect(conn_str)
        conn.autocommit = True
        return conn
    except Exception:
        try:
            import pymssql
            conn = pymssql.connect(server=db_server, user=db_user, password=db_password, database=db_name, timeout=5, as_dict=True, autocommit=True)
            return conn
        except Exception:
            # Fallback to SQLite
            conn = sqlite3.connect(sqlite_path)
            conn.row_factory = sqlite3.Row
            ensure_sqlite_schema(conn)
            return conn

def check_db_status():
    global DB_ONLINE
    # Trigger an initial sync to clear any pending records after migration
    threading.Thread(target=auto_sync_all, daemon=True).start()
    
    while True:
        # Reverting to real SQL Server connection check
        if USE_SQLITE:
            DB_ONLINE = True
            time.sleep(60)
            continue

        try:
            conn = get_db_connection()
            # If it's a real SQL Server connection (not the sqlite fallback)
            if not isinstance(conn, sqlite3.Connection):
                DB_ONLINE = True
                conn.close()
            else:
                DB_ONLINE = False
                # If it fell back to sqlite, we are "OFFLINE" relative to SQL Server
        except Exception:
            DB_ONLINE = False
            
        time.sleep(5) # Probing every 5 seconds for "instant" feeling

def start_health_check():
    t = threading.Thread(target=check_db_status)
    t.daemon = True
    t.start()
    
def ensure_sqlite_schema(conn):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            cargo TEXT DEFAULT 'Funcionario',
            role TEXT DEFAULT 'user',
            must_clear_cache INTEGER DEFAULT 0
        )
    """)
    # Migration for existing SQLite Users table
    try: c.execute("ALTER TABLE Users ADD COLUMN must_clear_cache INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE Users ADD COLUMN cargo TEXT DEFAULT 'Funcionario'")
    except: pass
    c.execute("""
        CREATE TABLE IF NOT EXISTS TimeRecords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            matricula TEXT NOT NULL,
            record_type TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            neighborhood TEXT,
            city TEXT,
            latitude FLOAT,
            longitude FLOAT,
            accuracy FLOAT,
            full_address TEXT,
            user_name TEXT,
            transaction_id TEXT UNIQUE,
            cargo TEXT DEFAULT 'Funcionario'
        );
        CREATE TABLE IF NOT EXISTS OfflineQueue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT NOT NULL,
            record_type TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            neighborhood TEXT,
            city TEXT,
            latitude FLOAT,
            longitude FLOAT,
            accuracy FLOAT,
            full_address TEXT,
            transaction_id TEXT UNIQUE,
            cargo TEXT DEFAULT 'Funcionario'
        );
    """)
    # Add columns if they don't exist
    new_cols = [
        ("TimeRecords", "latitude", "REAL"),
        ("TimeRecords", "longitude", "REAL"),
        ("TimeRecords", "accuracy", "REAL"),
        ("TimeRecords", "full_address", "TEXT"),
        ("OfflineQueue", "latitude", "REAL"),
        ("OfflineQueue", "longitude", "REAL"),
        ("OfflineQueue", "accuracy", "REAL"),
        ("OfflineQueue", "full_address", "TEXT"),
        ("TimeRecords", "matricula", "TEXT"),
        ("TimeRecords", "user_name", "TEXT"),
        ("OfflineQueue", "matricula", "TEXT"),
        ("OfflineQueue", "user_name", "TEXT"),
        ("TimeRecords", "transaction_id", "TEXT"),
        ("OfflineQueue", "transaction_id", "TEXT")
    ]
    for table, col, col_type in new_cols:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except: pass
        
    c.execute("""
        CREATE TABLE IF NOT EXISTS SystemConfig (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    # Default location edit password
    c.execute("INSERT OR IGNORE INTO SystemConfig (key, value) VALUES ('location_edit_password', 'admin123')")
    
    conn.commit()

def migrate_local_data():
    """Populates matricula and user_name in existing TimeRecords and OfflineQueue entries."""
    print("DEBUG: Starting local data migration...")
    try:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Build mapping
        cur.execute("SELECT id, matricula, name FROM Users")
        user_map = {r['id']: (r['matricula'], r['name']) for r in cur.fetchall()}
        
        # Update TimeRecords
        cur.execute("SELECT id, user_id FROM TimeRecords WHERE matricula IS NULL")
        to_update = cur.fetchall()
        for r in to_update:
            if r['user_id'] in user_map:
                m, n = user_map[r['user_id']]
                cur.execute("UPDATE TimeRecords SET matricula = ?, user_name = ? WHERE id = ?", (m, n, r['id']))
        
        # Update OfflineQueue
        cur.execute("SELECT id, user_id FROM OfflineQueue WHERE matricula IS NULL")
        to_update_q = cur.fetchall()
        for r in to_update_q:
            if r['user_id'] in user_map:
                m, n = user_map[r['user_id']]
                cur.execute("UPDATE OfflineQueue SET matricula = ?, user_name = ? WHERE id = ?", (m, n, r['id']))
        
        conn.commit()
        conn.close()
        print("DEBUG: Local data migration complete.")
    except Exception as e:
        print(f"DEBUG: Migration error: {e}")
    # The original instruction had conn.commit() here, but it should be inside the try block before conn.close()
    # or removed if the previous commit covers it. Given the structure, it's likely a copy-paste error.
    # I'll remove the redundant conn.commit() here as it's already done inside the try block.

def ensure_default_admin():
    try:
        admin_mat = os.getenv('ADMIN_MATRICULA', 'admin')
        admin_pass = os.getenv('ADMIN_PASSWORD', 'admin')
        admin_name = os.getenv('ADMIN_NAME', 'Administrador')
        sconn = sqlite3.connect(sqlite_path)
        sconn.row_factory = sqlite3.Row
        ensure_sqlite_schema(sconn)
        scur = sconn.cursor()
        scur.execute("SELECT 1 FROM Users WHERE matricula = ?", (admin_mat,))
        exists = scur.fetchone()
        if not exists:
            hashed = bcrypt.hashpw(admin_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            try:
                scur.execute("INSERT OR IGNORE INTO Users (matricula, password, name, role) VALUES (?, ?, ?, ?)", (admin_mat, hashed, admin_name, 'admin'))
                sconn.commit()
            except Exception:
                pass
        sconn.close()
    except Exception:
        pass




def sql_online():
    return DB_ONLINE

def get_ph(conn):
    """Returns the correct SQL placeholder based on the connection type."""
    if isinstance(conn, sqlite3.Connection):
        return '?'
    if 'pymssql' in str(type(conn)):
        return '%s'
    return '?'

def get_user_info_by_id(user_id, conn):
    """Returns (matricula, name) for a given user_id using the provided connection."""
    ph = get_ph(conn)
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        nolock = "" if is_sqlite else "WITH (NOLOCK)"
        cur.execute(f"SELECT matricula, name FROM Users {nolock} WHERE id = {ph}", (user_id,))
        row = cur.fetchone()
        if row:
            return rf(row, 'matricula'), rf(row, 'name')
    except:
        pass
    return None, None

def get_user_info_by_matricula(matricula, conn):
    """Returns (id, name) for a given matricula using the provided connection."""
    ph = get_ph(conn)
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cur = conn.cursor()
        nolock = "" if is_sqlite else "WITH (NOLOCK)"
        cur.execute(f"SELECT id, name FROM Users {nolock} WHERE matricula = {ph}", (matricula,))
        row = cur.fetchone()
        if row:
            return rf(row, 'id'), rf(row, 'name')
    except:
        pass
    return None, None


def rf(row, name):
    """
    Robustly fetch a column from a database row (sqlite3.Row, pyodbc.Row, dict, or tuple).
    """
    if row is None:
        return None
    try:
        # 1. Try dict-style access (sqlite3.Row, dict, pymssql as_dict)
        if hasattr(row, 'get'):
            return row.get(name)
        
        # 2. Try index/key access
        try:
            return row[name]
        except (TypeError, IndexError, KeyError):
            pass
            
        # 3. Try attribute access (pyodbc.Row)
        return getattr(row, name)
    except Exception:
        # 4. Final attempt: fallback to column indices if we know the row is a tuple and which column it is
        # This is a bit risky but helped if col order is fixed
        return None

# Auth Decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "") or ""
        parts = auth.split()
        token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else None
        if not token:
            return jsonify({"message": "Token is missing!"}), 401
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            # Favor matricula for cross-system stability
            curr_user_mat = data.get("matricula")
            if not curr_user_mat:
                # Fallback for old tokens if any
                curr_user_mat = str(data.get("user_id"))
            role = data["role"]
        except Exception as e:
            print(f"❌ Token validation failed: {str(e)}")
            return jsonify({"message": "Token is invalid!"}), 401
        return f(curr_user_mat, role, *args, **kwargs)
    return decorated

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# API Endpoints
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    
    
    cargo = data.get('cargo')
    if not cargo:
        cargo = 'Funcionario'
    
    conn = get_db_connection()
    ph = get_ph(conn)
    cursor = conn.cursor()
    
    try:
        # Ensure 'cargo' column exists on SQL Server if using it
        if not isinstance(conn, sqlite3.Connection):
            try: cursor.execute("ALTER TABLE Users ADD cargo NVARCHAR(100) DEFAULT 'Funcionario'")
            except: pass
            conn.commit()

        query = f"INSERT INTO Users (matricula, password, name, role, cargo) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})"
        cursor.execute(query, (data['matricula'], hashed_password, data['name'], 'user', cargo))
        try: conn.commit()
        except: pass
        # mirror to local sqlite for offline login
        try:
            sconn = sqlite3.connect(sqlite_path)
            sconn.row_factory = sqlite3.Row
            ensure_sqlite_schema(sconn)
            scur = sconn.cursor()
            scur.execute("INSERT OR IGNORE INTO Users (matricula, password, name, role, cargo) VALUES (?, ?, ?, ?, ?)",
                         (data['matricula'], hashed_password, data['name'], 'user', cargo))
            sconn.commit()
            sconn.close()
        except Exception:
            pass
        return jsonify({'message': 'User registered successfully!'}), 201
    except Exception as e:
        msg = str(e)
        if 'UNIQUE' in msg or 'unique' in msg or 'duplicate' in msg:
            return jsonify({'message': 'Matricula already exists!'}), 409
        return jsonify({'message': msg}), 500
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    conn = get_db_connection()
    ph = get_ph(conn)
    user = None
    is_sqlite = isinstance(conn, sqlite3.Connection)
    try:
        cursor = conn.cursor()
        if not is_sqlite:
            query = f"SELECT id, matricula, password, name, role, cargo FROM Users WITH (NOLOCK) WHERE matricula = {ph}"
        else:
            query = f"SELECT id, matricula, password, name, role, cargo FROM Users WHERE matricula = {ph}"
        cursor.execute(query, (data['matricula'],))
        user = cursor.fetchone()
    except Exception:
        user = None
    finally:
        try:
            conn.close()
        except Exception:
            pass
    
    # Fallback to local sqlite if not found on primary connection (if primary was SQL)
    if not user and not is_sqlite:
        try:
            sconn = sqlite3.connect(sqlite_path)
            sconn.row_factory = sqlite3.Row
            ensure_sqlite_schema(sconn)
            scur = sconn.cursor()
            scur = sconn.cursor()
            scur.execute("SELECT id, matricula, password, name, role, cargo FROM Users WHERE matricula = ?", (data['matricula'],))
            user = scur.fetchone()
            sconn.close()
        except Exception:
            user = None
    
    pw_field = rf(user, 'password')
    if user and pw_field and bcrypt.checkpw(data['password'].encode('utf-8'), pw_field.encode('utf-8')):
        # Mirror user to local sqlite for future offline login
        try:
            sconn = sqlite3.connect(sqlite_path)
            sconn.row_factory = sqlite3.Row
            ensure_sqlite_schema(sconn)
            scur = sconn.cursor()
            current_hash = rf(user, 'password')
            
            scur.execute("SELECT 1 FROM Users WHERE matricula = ?", (data['matricula'],))
            exists = scur.fetchone()
            if exists:
                 scur.execute("UPDATE Users SET password = ?, name = ?, role = ?, cargo = ? WHERE matricula = ?", 
                              (current_hash, rf(user, 'name'), rf(user, 'role'), rf(user, 'cargo'), data['matricula']))
            else:
                scur.execute("INSERT INTO Users (matricula, password, name, role, cargo) VALUES (?, ?, ?, ?, ?)",
                             (data['matricula'], current_hash, rf(user, 'name'), rf(user, 'role'), rf(user, 'cargo')))
            sconn.commit()
            sconn.close()
        except Exception:
            pass

        try:
            token = jwt.encode({
                'matricula': rf(user, 'matricula'),
                'user_id': rf(user, 'id'), # keep for backward compat if needed
                'role': rf(user, 'role'),
                'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            
            # Trigger background sync for this user immediately
            threading.Thread(target=perform_sync_for_user, args=(rf(user, 'matricula'),), daemon=True).start()
            
            return jsonify({'token': token, 'role': rf(user, 'role'), 'name': rf(user, 'name'), 'cargo': rf(user, 'cargo')})
        except Exception as e:
            return jsonify({'message': f'Internal Server Error: {str(e)}'}), 500
    
    return jsonify({'message': 'Invalid credentials!'}), 401

@app.route('/api/punch', methods=['POST'])
@token_required
def punch(curr_user_mat, role):
    data = request.get_json()
    # Expecting: type, neighborhood, city
    
    conn = get_db_connection()
    # Determine basic status
    is_sqlite = isinstance(conn, sqlite3.Connection)
    ph = get_ph(conn)

    current_time_raw = datetime.datetime.now(pytz.timezone('America/Sao_Paulo')).replace(tzinfo=None)
    current_time = current_time_raw.replace(microsecond=0) # Standardize to seconds
    transaction_id = data.get('transaction_id')
    
    # fetch denormalized user fields if available
    user_matricula = curr_user_mat
    sql_user_id, user_name = get_user_info_by_matricula(user_matricula, conn) # Use 'conn' for potential SQL Server
    
    # Also find local user_id to catch orphaned local records
    lconn = sqlite3.connect(sqlite_path)
    lconn.row_factory = sqlite3.Row
    local_user_id, l_user_name = get_user_info_by_matricula(user_matricula, lconn)
    lconn.close()

    if not user_name:
         user_name = l_user_name
    
    # Fallback to local user_id if SQL one not found (rare if online)
    sync_user_id = sql_user_id if sql_user_id else local_user_id
    
    # --- ATOMIC SCHEMA AND DUPLICATE PROTECTION ---
    def ensure_transaction_schema(db_conn):
        try:
            curs = db_conn.cursor()
            is_sq = isinstance(db_conn, sqlite3.Connection)
            tables = ["TimeRecords", "OfflineQueue"] if is_sq else ["TimeRecords"]
            for table in tables:
                if is_sq:
                    try: curs.execute(f"ALTER TABLE {table} ADD COLUMN transaction_id TEXT")
                    except: pass
                    try: curs.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table}_txid ON {table}(transaction_id)")
                    except: pass
                    # Enforce Cargo Column in TimeRecords/OfflineQueue for SQLite
                    try: curs.execute(f"ALTER TABLE {table} ADD COLUMN cargo TEXT DEFAULT 'Funcionario'")
                    except: pass
                else:
                    try: curs.execute(f"ALTER TABLE {table} ADD transaction_id NVARCHAR(100)")
                    except: pass
                    try: curs.execute(f"CREATE UNIQUE INDEX idx_{table}_txid ON {table}(transaction_id) WHERE transaction_id IS NOT NULL")
                    except: pass
                    # Enforce Cargo Column in TimeRecords for SQL Server
                    try: curs.execute(f"ALTER TABLE {table} ADD cargo NVARCHAR(100) DEFAULT 'Funcionario'")
                    except: pass
            db_conn.commit()
        except: pass

    ensure_transaction_schema(conn)
    qconn_mig = sqlite3.connect(sqlite_path); ensure_transaction_schema(qconn_mig); qconn_mig.close()
    
    def check_exists_robust(db_conn, table_name):
        try:
            curs = db_conn.cursor()
            is_sq = isinstance(db_conn, sqlite3.Connection); p = get_ph(db_conn)
            if transaction_id:
                curs.execute(f"SELECT id FROM {table_name} WHERE transaction_id = {p}", (transaction_id,))
                if curs.fetchone():
                    print(f"DEBUG: Duplicate found by transaction_id={transaction_id} in {table_name}")
                    return True
            today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            q = f"SELECT {'TOP 1 id' if not is_sq else 'id'} FROM {table_name} {'WITH (NOLOCK)' if not is_sq else ''} WHERE matricula = {p} AND record_type = {p} AND timestamp >= {p} {'LIMIT 1' if is_sq else ''}"
            curs.execute(q, (user_matricula, data['type'], today_start))
            if curs.fetchone():
                print(f"DEBUG: Daily duplicate found for {user_matricula} ({data['type']}) in {table_name}")
                return True
        except Exception as e:
            print(f"DEBUG: Error in check_exists_robust: {e}")
        return False

    if check_exists_robust(conn, "TimeRecords"): return jsonify({'message': 'Ponto já registrado!'}), 409
    qconn_chk = sqlite3.connect(sqlite_path)
    if check_exists_robust(qconn_chk, "OfflineQueue") or check_exists_robust(qconn_chk, "TimeRecords"):
        qconn_chk.close(); return jsonify({'message': 'Ponto já registrado!'}), 409
    qconn_chk.close()
    # --- END ATOMIC PROTECTION ---

    # 1. Try Online Insert if applicable
    inserted_online = False
    
    # Get Current Cargo
    user_cargo = 'Funcionario'
    try:
        if sql_user_id:
             c_cur = conn.cursor()
             p = get_ph(conn)
             nolock = "" if is_sqlite else "WITH (NOLOCK)"
             c_cur.execute(f"SELECT cargo FROM Users {nolock} WHERE id = {p}", (sql_user_id,))
             r = c_cur.fetchone()
             if r: user_cargo = rf(r, 'cargo') or 'Funcionario'
        else:
             # Try local if sql failed
             lconn = sqlite3.connect(sqlite_path)
             lcur = lconn.cursor()
             lcur.execute("SELECT cargo FROM Users WHERE matricula = ?", (user_matricula,))
             r = lcur.fetchone()
             lconn.close()
             if r: user_cargo = r[0] or 'Funcionario'
    except: pass
    
    # If using SQL Server OR if we are in local VS Code mode (USE_SQLITE is true)
    # the receipt of a /api/punch request means we should save to TimeRecords immediately.
    # But now, "Online" means SQL Server is reachable.
    if (not is_sqlite and DB_ONLINE) or USE_SQLITE:
        try:
            cursor = conn.cursor()
            
            # Ensure SQL Server columns exist (one-time check attempt)
            if not is_sqlite:
                for col, col_type in [
                    ('latitude', 'FLOAT'), ('longitude', 'FLOAT'), ('accuracy', 'FLOAT'), 
                    ('neighborhood', 'NVARCHAR(255)'), ('city', 'NVARCHAR(255)'), 
                    ('full_address', 'NVARCHAR(500)'), ('user_name', 'NVARCHAR(255)'),
                    ('cargo', 'NVARCHAR(100)')
                ]:
                    try: cursor.execute(f"ALTER TABLE TimeRecords ADD {col} {col_type}")
                    except: pass
                conn.commit()

            query = f"""
                INSERT INTO TimeRecords 
                (user_id, matricula, record_type, timestamp, latitude, longitude, accuracy, neighborhood, city, full_address, user_name, transaction_id, cargo) 
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """
            cursor.execute(query, (
                sync_user_id, user_matricula, data['type'], current_time, 
                data.get('latitude'), data.get('longitude'), data.get('accuracy'), 
                data.get('neighborhood'), data.get('city'), data.get('full_address'),
                user_name, transaction_id, user_cargo
            ))
            # Mark as successfully online
            inserted_online = True
            
            # --- v6.3: RESTORE MIRRORING ---
            # Immediate local mirroring to ensure history is always updated
            if not is_sqlite: # It reached SQL Server, so mirror locally
                try:
                    qconn = sqlite3.connect(sqlite_path); qconn.row_factory = sqlite3.Row; ensure_sqlite_schema(qconn)
                    # Include Cargo in mirror
                    qconn.execute("""
                        INSERT OR IGNORE INTO TimeRecords 
                        (user_id, matricula, user_name, record_type, neighborhood, city, latitude, longitude, accuracy, full_address, timestamp, transaction_id, cargo) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (sync_user_id, user_matricula, user_name, data['type'], data.get('neighborhood'), data.get('city'), 
                          data.get('latitude'), data.get('longitude'), data.get('accuracy'), data.get('full_address'), current_time, transaction_id, user_cargo))
                    qconn.commit()
                    qconn.close()
                except Exception as mir_err:
                    print(f"DEBUG: Background Mirroring failed: {mir_err}") # Non-blocking for the user
            # -------------------------------
            
        except Exception as e:
            print(f"Online insert failed: {e}")
            if not USE_SQLITE: 
                 pass 
    
    # 2. If Online failed (and not in local-kv mode), save to OfflineQueue (Forward Store)
    if not inserted_online:
        try:
            sconn = sqlite3.connect(sqlite_path)
            ensure_sqlite_schema(sconn)
            # Ensure cargo col in OfflineQueue if ensure_sqlite_schema didn't catch it
            try: sconn.execute("ALTER TABLE OfflineQueue ADD COLUMN cargo TEXT DEFAULT 'Funcionario'")
            except: pass
            
            scur = sconn.cursor()
            scur.execute("INSERT OR IGNORE INTO OfflineQueue (matricula, record_type, timestamp, latitude, longitude, accuracy, neighborhood, city, full_address, transaction_id, cargo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                         (user_matricula, data['type'], current_time, data.get('latitude'), data.get('longitude'), data.get('accuracy'), data.get('neighborhood'), data.get('city'), data.get('full_address'), transaction_id, user_cargo))
            sconn.commit()
            sconn.close()
        except Exception as e:
            print(f"Offline queue insert failed: {e}")
            try: conn.close()
            except: pass
            return jsonify({'message': 'Erro ao salvar ponto'}), 500
            
    try: conn.close()
    except: pass
    return jsonify({'message': 'Ponto registrado com sucesso!', 'offline': not inserted_online}), 201

@app.route('/api/history', methods=['GET'])
@token_required
def history(curr_user_mat, role):
    conn = get_db_connection()
    try:
        is_sqlite = isinstance(conn, sqlite3.Connection)
        ph = get_ph(conn)
        
        user_matricula = curr_user_mat
        clear_cache_signal = False

        # Get user info for inclusive filtering
        sql_user_id, user_name = None, None
        local_user_id, l_user_name = None, None
        if sql_online():
            try:
                # Use a temp connection to avoid mixing with 'conn' if it's already used
                tconn = get_db_connection()
                sql_user_id, user_name = get_user_info_by_matricula(user_matricula, tconn)
                tconn.close()
            except: pass
        
        try:
            lconn = sqlite3.connect(sqlite_path)
            lconn.row_factory = sqlite3.Row
            # Check for cache clearing signal
            try:
                scur = lconn.cursor()
                scur.execute("SELECT must_clear_cache FROM Users WHERE matricula = ?", (user_matricula,))
                user_row = scur.fetchone()
                if user_row and rf(user_row, 'must_clear_cache') == 1:
                    clear_cache_signal = True
                    scur.execute("UPDATE Users SET must_clear_cache = 0 WHERE matricula = ?", (user_matricula,))
                    lconn.commit()
            except: pass
            
            local_user_id, l_user_name = get_user_info_by_matricula(user_matricula, lconn)
            lconn.close()
        except: pass

        # Also check SQL Server for the signal if reachable
        if not clear_cache_signal and sql_online():
            try:
                tconn = get_db_connection()
                if not isinstance(tconn, sqlite3.Connection):
                    tsph = get_ph(tconn)
                    tcur = tconn.cursor()
                    try: tcur.execute("ALTER TABLE Users ADD must_clear_cache INT DEFAULT 0")
                    except: pass
                    tcur.execute(f"SELECT must_clear_cache FROM Users WHERE matricula = {tsph}", (user_matricula,))
                    s_row = tcur.fetchone()
                    if s_row and rf(s_row, 'must_clear_cache') == 1:
                        clear_cache_signal = True
                        tcur.execute(f"UPDATE Users SET must_clear_cache = 0 WHERE matricula = {tsph}", (user_matricula,))
                        tconn.commit()
                tconn.close()
            except: pass

        records = []
        seen = set()
        
        sql_fetch_failed = False
        # Try SQL Server first
        try:
            # Try via get_db_connection() which might be SQL Server
            cursor = conn.cursor()
            nolock = "" if is_sqlite else "WITH (NOLOCK)"
            if not is_sqlite:
                cursor.execute(f"""
                    SELECT record_type, timestamp, neighborhood, city, transaction_id
                    FROM TimeRecords {nolock}
                    WHERE matricula = {ph} 
                      AND timestamp >= DATEADD(day, -90, GETDATE())
                    ORDER BY timestamp DESC
                """, (user_matricula,))
                rows = cursor.fetchall()
                for row in rows:
                    ts = rf(row, 'timestamp')
                    if isinstance(ts, datetime.datetime):
                        ts = ts.strftime('%Y-%m-%d %H:%M:%S')
                    tx_id = rf(row, 'transaction_id')
                    tx_id_str = str(tx_id) if tx_id else None
                    key = (rf(row, 'record_type'), str(ts).split('.')[0])
                    if key not in seen and (not tx_id_str or tx_id_str not in seen):
                        seen.add(key)
                        if tx_id_str: seen.add(tx_id_str)
                        records.append({
                            'type': rf(row, 'record_type'),
                            'timestamp': ts,
                            'neighborhood': rf(row, 'neighborhood'),
                            'city': rf(row, 'city'),
                            'pending': False,
                            'transaction_id': tx_id
                        })
        except Exception as e:
            print(f"DEBUG: SQL Fetch failed: {e}")
            sql_fetch_failed = True

        # Now ALWAYS check the local mirror (SQLite TimeRecords) to merge/fill gaps
        try:
            lconn = sqlite3.connect(sqlite_path)
            lconn.row_factory = sqlite3.Row
            lcur = lconn.cursor()
            print(f"DEBUG: Querying local history for matricula={user_matricula}")
            lcur.execute(f"""
                SELECT record_type, timestamp, neighborhood, city, transaction_id
                FROM TimeRecords 
                WHERE matricula = ? 
                  AND timestamp >= date('now', '-90 days')
                ORDER BY timestamp DESC
            """, (user_matricula,))
            rows = lcur.fetchall()
            print(f"DEBUG: Local history found {len(rows)} rows.")
            for row in rows:
                ts = rf(row, 'timestamp')
                if isinstance(ts, datetime.datetime):
                    ts = ts.strftime('%Y-%m-%d %H:%M:%S')
                tx_id = rf(row, 'transaction_id')
                tx_id_str = str(tx_id) if tx_id else None
                key = (rf(row, 'record_type'), str(ts).split('.')[0])
                if key not in seen and (not tx_id_str or tx_id_str not in seen):
                    seen.add(key)
                    if tx_id_str: seen.add(tx_id_str)
                    records.append({
                        'type': rf(row, 'record_type'),
                        'timestamp': ts,
                        'neighborhood': rf(row, 'neighborhood'),
                        'city': rf(row, 'city'),
                        'pending': False,
                        'transaction_id': tx_id
                    })
            lconn.close()
        except:
            pass

        # Finally add pending records from OfflineQueue
        history_list = records + self_pending_records(user_matricula)
        response_data = history_list
        if clear_cache_signal:
            # Wrap in an object if we need to signal cache clearing
            return jsonify({'records': history_list, 'clear_cache': True})
        
        return jsonify(history_list)
    finally:
        try:
            conn.close()
        except:
            pass

def self_pending_records(user_matricula):
    """Helper to fetch only pending records for a user from OfflineQueue."""
    pending = []
    try:
        sconn = sqlite3.connect(sqlite_path)
        sconn.row_factory = sqlite3.Row
        scur = sconn.cursor()
        scur.execute("SELECT record_type, timestamp, neighborhood, city, transaction_id FROM OfflineQueue WHERE matricula = ? ORDER BY timestamp DESC", (user_matricula,))
        rows = scur.fetchall()
        for row in rows:
            ts = rf(row, 'timestamp')
            if isinstance(ts, datetime.datetime):
                ts = ts.strftime('%Y-%m-%d %H:%M:%S')
            pending.append({
                'type': rf(row, 'record_type'),
                'timestamp': ts,
                'neighborhood': rf(row, 'neighborhood'),
                'city': rf(row, 'city'),
                'pending': True,
                'transaction_id': rf(row, 'transaction_id')
            })
        sconn.close()
    except: pass
    return pending

@app.route('/api/online')
def online():
    # Se o endpoint foi chamado, o servidor está online.
    # Verificamos o banco apenas para informação.
    db_ok = sql_online()
    return jsonify({'online': True, 'db_online': db_ok}), 200

@app.route('/api/user/report', methods=['GET'])
@token_required
def get_user_report(curr_user_mat, role):
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_matricula = curr_user_mat
        
        records = []
        seen = set()
        user_name = "Usuário"

        # 1. Try SQL Server
        conn_primary = get_db_connection()
        try:
            if not isinstance(conn_primary, sqlite3.Connection):
                cursor = conn_primary.cursor()
                query = f"""
                    SELECT t.matricula, t.user_name AS name,
                           t.record_type, t.timestamp, t.neighborhood, t.city,
                           t.latitude, t.longitude, t.accuracy, t.full_address
                    FROM TimeRecords t
                    WHERE t.matricula = %s
                """
                params = [user_matricula]
                if start_date:
                    query += " AND CAST(t.timestamp AS DATE) >= %s"
                    params.append(start_date)
                if end_date:
                    query += " AND CAST(t.timestamp AS DATE) <= %s"
                    params.append(end_date)
                
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    ts = rf(row, 'timestamp')
                    ts_str = ts.strftime('%Y-%m-%d %H:%M:%S') if isinstance(ts, datetime.datetime) else str(ts)
                    key = (rf(row, 'record_type'), ts_str.split('.')[0])
                    if key not in seen:
                        seen.add(key)
                        records.append({
                            'matricula': rf(row, 'matricula'),
                            'name': rf(row, 'name'),
                            'type': rf(row, 'record_type'),
                            'timestamp': ts_str,
                            'neighborhood': rf(row, 'neighborhood'),
                            'city': rf(row, 'city'),
                            'latitude': rf(row, 'latitude'),
                            'longitude': rf(row, 'longitude'),
                            'accuracy': rf(row, 'accuracy'),
                            'full_address': rf(row, 'full_address')
                        })
                        user_name = rf(row, 'name')
        except Exception as e:
            print(f"Error fetching from SQL Server for report: {e}")
        finally:
            try: conn_primary.close()
            except: pass

        # 2. Always merge from local mirror (SQLite)
        try:
            lconn = sqlite3.connect(sqlite_path)
            lconn.row_factory = sqlite3.Row
            lcur = lconn.cursor()
            query = "SELECT matricula, user_name as name, record_type, timestamp, neighborhood, city, latitude, longitude, accuracy, full_address FROM TimeRecords WHERE matricula = ?"
            params = [user_matricula]
            if start_date:
                query += " AND date(timestamp) >= ?"
                params.append(start_date)
            if end_date:
                query += " AND date(timestamp) <= ?"
                params.append(end_date)
            
            lcur.execute(query, params)
            for row in lcur.fetchall():
                ts = rf(row, 'timestamp')
                ts_str = str(ts).split('.')[0]
                key = (rf(row, 'record_type'), ts_str)
                if key not in seen:
                    seen.add(key)
                    records.append({
                        'matricula': rf(row, 'matricula'),
                        'name': rf(row, 'name'),
                        'type': rf(row, 'record_type'),
                        'timestamp': ts_str,
                        'neighborhood': rf(row, 'neighborhood'),
                        'city': rf(row, 'city'),
                        'latitude': rf(row, 'latitude'),
                        'longitude': rf(row, 'longitude'),
                        'accuracy': rf(row, 'accuracy'),
                        'full_address': rf(row, 'full_address')
                    })
            lconn.close()
        except Exception as e:
            print(f"Error fetching from SQLite mirror for report: {e}")
        finally:
            try:
                conn_primary.close()
            except:
                pass

        # 3. Final Excel Generation
        # Sort merged records by timestamp desc
        records.sort(key=lambda x: (x['timestamp'] or ""), reverse=True)

        # Retrieve cargo for the user
        user_cargo = "Funcionario"
        try:
             c_conn = get_db_connection()
             c_ph = get_ph(c_conn)
             c_cur = c_conn.cursor()
             nolock = "" if isinstance(c_conn, sqlite3.Connection) else "WITH (NOLOCK)"
             q_cargo = f"SELECT cargo FROM Users {nolock} WHERE matricula = {c_ph}"
             c_cur.execute(q_cargo, (user_matricula,))
             c_row = c_cur.fetchone()
             if c_row:
                 user_cargo = rf(c_row, 'cargo') or "Funcionario"
             c_conn.close()
        except: pass

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Meus Registros"
        ws.append(["Matricula", "Nome", "Cargo", "Tipo", "Data/Hora", "Bairro", "Cidade", "Latitude", "Longitude", "Precisão (m)", "Endereço Completo"])
        
        for r in records:
            ws.append([
                r['matricula'], r['name'], user_cargo, r['type'], r['timestamp'],
                r['neighborhood'], r['city'], r['latitude'], r['longitude'],
                r['accuracy'], r['full_address']
            ])
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(output, download_name="meus_registros.xlsx", as_attachment=True)
    except Exception as e:
        print(f"CRITICAL REPORT ERROR: {e}")
        return jsonify({'message': f'Erro crítico no relatório: {str(e)}'}), 500

@app.route('/api/admin/users', methods=['GET'])
@token_required
def get_users(curr_user_mat, role):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        is_sqlite = isinstance(conn, sqlite3.Connection)
        nolock = "" if is_sqlite else "WITH (NOLOCK)"
        cursor.execute(f"SELECT id, matricula, name, role, cargo FROM Users {nolock}")
        rows = cursor.fetchall()
        users = []
        for r in rows:
            users.append({
                'id': rf(r, 'id'),
                'matricula': rf(r, 'matricula'),
                'name': rf(r, 'name'),
                'role': rf(r, 'role'),
                'cargo': rf(r, 'cargo')
            })
        return jsonify(users)
    finally:
        try:
            conn.close()
        except:
            pass

@app.route('/api/admin/users', methods=['POST'])
@token_required
def create_user_admin(curr_user_mat, role):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    data = request.json
    matricula = data.get('matricula')
    name = data.get('name')
    password_raw = data.get('password')
    new_role = data.get('role', 'user')
    cargo = data.get('cargo')
    if not cargo:
        cargo = 'Funcionario'
    if not matricula or not name or not password_raw:
        return jsonify({'message': 'Dados obrigatórios faltando'}), 400
    
    hashed = bcrypt.hashpw(password_raw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_db_connection()
    ph = get_ph(conn)
    try:
        cursor = conn.cursor()
        query = f"INSERT INTO Users (matricula, password, name, role, cargo) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})"
        cursor.execute(query, (matricula, hashed, name, new_role, cargo))
        if isinstance(conn, sqlite3.Connection):
            conn.commit()
        elif ph == '?': 
            conn.commit()
        # mirror locally
        try:
            sconn = sqlite3.connect(sqlite_path)
            scur = sconn.cursor()
            ensure_sqlite_schema(sconn)
            scur.execute("INSERT OR REPLACE INTO Users (matricula, password, name, role, cargo) VALUES (?, ?, ?, ?, ?)", (matricula, hashed, name, new_role, cargo))
            sconn.commit()
            sconn.close()
        except: pass
        return jsonify({'message': 'Usuário criado'}), 201
    except Exception as e:
        msg = str(e)
        if 'UNIQUE' in msg or 'duplicate' in msg:
            return jsonify({'message': 'Matrícula já existe'}), 409
        return jsonify({'message': msg}), 500
    finally:
        try:
            conn.close()
        except: pass

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(curr_user_mat, role, user_id):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    data = request.json
    conn = get_db_connection()
    ph = get_ph(conn)
    fields = []
    values = []
    hashed = None
    if 'matricula' in data and data['matricula']:
        fields.append(f'matricula = {ph}')
        values.append(data['matricula'])
    if 'name' in data and data['name']:
        fields.append(f'name = {ph}')
        values.append(data['name'])
    if 'role' in data and data['role']:
        fields.append(f'role = {ph}')
        values.append(data['role'])
    if 'cargo' in data: # allow updating cargo even to empty if desired, or check for value
        fields.append(f'cargo = {ph}')
        values.append(data['cargo'])
    if 'password' in data and data['password']:
        hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        fields.append(f'password = {ph}')
        values.append(hashed)
    
    if not fields:
        return jsonify({'message': 'Nada para atualizar'}), 400
        
    try:
        cursor = conn.cursor()
        # Fetch old matricula first for local mirror update
        is_sqlite = isinstance(conn, sqlite3.Connection)
        nolock = "" if is_sqlite else "WITH (NOLOCK)"
        cursor.execute(f"SELECT matricula FROM Users {nolock} WHERE id = {ph}", (user_id,))
        old_row = cursor.fetchone()
        old_mat = rf(old_row, 'matricula') if old_row else None

        query = f"UPDATE Users SET {', '.join(fields)} WHERE id = {ph}"
        values.append(user_id)
        cursor.execute(query, tuple(values))
        if isinstance(conn, sqlite3.Connection) or ph == '?':
            conn.commit()
            
        # Mirror update locally using old_mat
        if old_mat:
            try:
                sconn = sqlite3.connect(sqlite_path)
                ensure_sqlite_schema(sconn)
                scur = sconn.cursor()
                lfields = []
                lvals = []
                if 'matricula' in data: lfields.append("matricula = ?"); lvals.append(data['matricula'])
                if 'name' in data: lfields.append("name = ?"); lvals.append(data['name'])
                if 'role' in data: lfields.append("role = ?"); lvals.append(data['role'])
                if 'cargo' in data: lfields.append("cargo = ?"); lvals.append(data['cargo'])
                if hashed: lfields.append("password = ?"); lvals.append(hashed)
                if lfields:
                    lvals.append(old_mat)
                    scur.execute(f"UPDATE Users SET {', '.join(lfields)} WHERE matricula = ?", tuple(lvals))
                    sconn.commit()
                sconn.close()
            except: pass
            
        return jsonify({'message': 'Usuário atualizado'}), 200
    except Exception as e:
        msg = str(e)
        if 'UNIQUE' in msg or 'duplicate' in msg:
            return jsonify({'message': 'Matrícula já existe'}), 409
        return jsonify({'message': msg}), 500
    finally:
        try: conn.close()
        except: pass

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(curr_user_mat, role, user_id):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    conn = get_db_connection()
    ph = get_ph(conn)
    cursor = conn.cursor()
    try:
        is_sqlite = isinstance(conn, sqlite3.Connection)
        nolock = "" if is_sqlite else "WITH (NOLOCK)"
        # Fetch matricula before delete
        cursor.execute(f"SELECT matricula FROM Users {nolock} WHERE id = {ph}", (user_id,))
        row = cursor.fetchone()
        mat = rf(row, 'matricula') if row else None
        
        cursor.execute(f"DELETE FROM TimeRecords WHERE user_id = {ph}", (user_id,))
        cursor.execute(f"DELETE FROM Users WHERE id = {ph}", (user_id,))
        if is_sqlite or ph == '?': conn.commit()
        
        if mat:
            try:
                sconn = sqlite3.connect(sqlite_path)
                scur = sconn.cursor()
                scur.execute("DELETE FROM Users WHERE matricula = ?", (mat,))
                sconn.commit()
                sconn.close()
            except: pass
        return jsonify({'message': 'Usuário excluído'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        try: conn.close()
        except: pass

@app.route('/api/admin/users/bulk-delete', methods=['POST'])
@token_required
def bulk_delete_users(curr_user_mat, role):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    data = request.json
    ids = data.get('user_ids', [])
    if not ids: return jsonify({'message': 'Nenhum selecionado'}), 400
    
    conn = get_db_connection()
    ph = get_ph(conn)
    cursor = conn.cursor()
    try:
        is_sqlite = isinstance(conn, sqlite3.Connection)
        nolock = "" if is_sqlite else "WITH (NOLOCK)"
        placeholders = ', '.join([ph]*len(ids))
        
        # Get matriculas for local delete
        cursor.execute(f"SELECT matricula FROM Users {nolock} WHERE id IN ({placeholders})", tuple(ids))
        mats = [rf(r, 'matricula') for r in cursor.fetchall()]
        
        cursor.execute(f"DELETE FROM TimeRecords WHERE user_id IN ({placeholders})", tuple(ids))
        cursor.execute(f"DELETE FROM Users WHERE id IN ({placeholders})", tuple(ids))
        if is_sqlite or ph == '?': conn.commit()
        
        if mats:
            try:
                sconn = sqlite3.connect(sqlite_path)
                scur = sconn.cursor()
                m_ph = ', '.join(['?']*len(mats))
                scur.execute(f"DELETE FROM Users WHERE matricula IN ({m_ph})", tuple(mats))
                sconn.commit()
                sconn.close()
            except: pass
        return jsonify({'message': f'{len(ids)} excluídos'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        try: conn.close()
        except: pass

@app.route('/api/admin/clear_records', methods=['POST'])
@token_required
def admin_clear_records(curr_user_mat, role):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized!'}), 403
    
    data = request.get_json()
    target_matricula = data.get('matricula')
    if not target_matricula:
        return jsonify({'message': 'Matricula required!'}), 400

    # 1. Clear from primary connection (could be SQL or SQLite)
    conn = get_db_connection()
    try:
        ph = get_ph(conn)
        cursor = conn.cursor()
        # Delete from TimeRecords
        cursor.execute(f"DELETE FROM TimeRecords WHERE matricula = {ph}", (target_matricula,))
        # Set clear cache flag
        try:
            is_sqlite = isinstance(conn, sqlite3.Connection)
            if not is_sqlite:
                try: cursor.execute("ALTER TABLE Users ADD must_clear_cache INT DEFAULT 0")
                except: pass
            cursor.execute(f"UPDATE Users SET must_clear_cache = 1 WHERE matricula = {ph}", (target_matricula,))
        except: pass
        
        if ph == '?' or isinstance(conn, sqlite3.Connection):
            conn.commit()
    except Exception as e:
        print(f"Error in admin_clear_records primary: {e}")
    finally:
        conn.close()

    # 2. Clear from local SQLite specifically
    try:
        lconn = sqlite3.connect(sqlite_path)
        lcur = lconn.cursor()
        lcur.execute("DELETE FROM TimeRecords WHERE matricula = ?", (target_matricula,))
        lcur.execute("DELETE FROM OfflineQueue WHERE matricula = ?", (target_matricula,))
        lcur.execute("UPDATE Users SET must_clear_cache = 1 WHERE matricula = ?", (target_matricula,))
        lconn.commit()
        lconn.close()
    except Exception as e:
        print(f"Error in admin_clear_records local: {e}")

    return jsonify({'message': 'Records cleared successfully!'}), 200

@app.route('/api/config/location-password', methods=['GET'])
def get_location_password():
    # Publicly accessible but only if we want to. 
    # To keep it secure, we could require a token, but the user wants to enter it in the dashboard.
    # So the dashboard needs to know what it is or the server needs to verify it.
    # Better: the dashboard sends the password to the server to check.
    # But for simplicity and matching current logic (client-side check), we'll provide it.
    try:
        conn = sqlite3.connect(sqlite_path)
        cur = conn.cursor()
        cur.execute("SELECT value FROM SystemConfig WHERE key = 'location_edit_password'")
        row = cur.fetchone()
        conn.close()
        return jsonify({'password': row[0] if row else 'admin123'})
    except:
        return jsonify({'password': 'admin123'})

@app.route('/api/admin/config', methods=['GET'])
@token_required
def get_admin_config(curr_user_mat, role):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    try:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM SystemConfig")
        rows = cur.fetchall()
        conn.close()
        return jsonify({r['key']: r['value'] for r in rows})
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/admin/config', methods=['POST'])
@token_required
def update_admin_config(curr_user_mat, role):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    data = request.get_json()
    try:
        conn = sqlite3.connect(sqlite_path)
        cur = conn.cursor()
        for key, value in data.items():
            cur.execute("INSERT OR REPLACE INTO SystemConfig (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Configuration updated successfully'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/api/admin/report', methods=['GET'])
@token_required
def get_admin_report_excel(curr_user_mat, role):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    target_user_id = request.args.get('user_id')
    fmt = request.args.get('format', 'excel') # excel or json
    
    conn = get_db_connection()
    ph = get_ph(conn)
    try:

        cursor = conn.cursor()
        query = """
            SELECT t.matricula, t.user_name AS name,
                   t.record_type, t.timestamp, t.neighborhood, t.city,
                   t.latitude, t.longitude, t.accuracy, t.full_address
            FROM TimeRecords t
        """
        params = []
        if target_user_id:
            query += f" WHERE t.user_id = {ph}"
            params.append(target_user_id)
        query += " ORDER BY t.timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()

        if fmt == 'json':
             # Return raw data for frontend PDF generation
             records = []
             for r in rows:
                 records.append({
                     'matricula': rf(r, 'matricula'),
                     'name': rf(r, 'name'),
                     'type': rf(r, 'record_type'),
                     'timestamp': rf(r, 'timestamp'),
                     'neighborhood': rf(r, 'neighborhood'),
                     'city': rf(r, 'city'),
                     'full_address': rf(r, 'full_address')
                 })
             return jsonify(records)
        
        # Build Cargo Map
        cargo_map = {}
        try:
            c_conn = get_db_connection()
            c_cur = c_conn.cursor()
            nolock = "" if isinstance(c_conn, sqlite3.Connection) else "WITH (NOLOCK)"
            c_cur.execute(f"SELECT matricula, cargo FROM Users {nolock}")
            for cr in c_cur.fetchall():
                cargo_map[rf(cr, 'matricula')] = rf(cr, 'cargo')
            c_conn.close()
        except: pass

        wb = openpyxl.Workbook()
        if target_user_id:
            ws = wb.active
            ws.title = "Relatorio"
            ws.append(["Matricula", "Nome", "Cargo", "Tipo", "Data/Hora", "Bairro", "Cidade", "Latitude", "Longitude", "Precisão (m)", "Endereço Completo"])
            for r in rows:
                mat = rf(r,'matricula')
                c = cargo_map.get(mat, 'Funcionario')
                ws.append([mat, rf(r,'name'), c, rf(r,'record_type'), rf(r,'timestamp'), rf(r,'neighborhood'), rf(r,'city'), rf(r,'latitude'), rf(r,'longitude'), rf(r,'accuracy'), rf(r,'full_address')])
        else:
            wb.remove(wb.active)
            groups = {}
            for r in rows:
                k = (rf(r,'matricula'), rf(r,'name'))
                groups.setdefault(k, []).append(r)
            for (m, n), items in groups.items():
                ws = wb.create_sheet(title=(n or m or "User")[:30])
                ws.append(["Matricula", "Nome", "Cargo", "Tipo", "Data/Hora", "Bairro", "Cidade", "Latitude", "Longitude", "Precisão (m)", "Endereço Completo"])
                for r in items:
                    mat = rf(r,'matricula')
                    c = cargo_map.get(mat, 'Funcionario')
                    ws.append([mat, rf(r,'name'), c, rf(r,'record_type'), rf(r,'timestamp'), rf(r,'neighborhood'), rf(r,'city'), rf(r,'latitude'), rf(r,'longitude'), rf(r,'accuracy'), rf(r,'full_address')])
        
        out = BytesIO()
        wb.save(out)
        out.seek(0)
        return send_file(out, download_name="relatorio_admin.xlsx", as_attachment=True)
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        try: conn.close()
        except: pass

@app.route('/api/admin/export', methods=['GET'])
@token_required
def export_excel_legacy(curr_user_mat, role):
    return get_admin_report_excel(curr_user_mat, role)

@app.route('/api/admin/sync_all', methods=['POST'])
@token_required
def sync_all_users_admin(curr_user_mat, role):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    refresh_local_users()
    return jsonify({'message': 'Sincronização de usuários solicitada'}), 200

def refresh_local_users():
    """Helper to pull users from SQL into local SQLite."""
    try:
        conn = get_db_connection()
        if isinstance(conn, sqlite3.Connection):
            return # Already strictly local
        cursor = conn.cursor()
        cursor.execute("SELECT matricula, password, name, role, cargo FROM Users WITH (NOLOCK)")
        users = cursor.fetchall()
        
        sconn = sqlite3.connect(sqlite_path)
        scur = sconn.cursor()
        ensure_sqlite_schema(sconn)
        for u in users:
            scur.execute("INSERT OR REPLACE INTO Users (matricula, password, name, role, cargo) VALUES (?, ?, ?, ?, ?)", 
                         (rf(u,'matricula'), rf(u,'password'), rf(u,'name'), rf(u,'role'), rf(u,'cargo')))
        sconn.commit()
        sconn.close()
        conn.close()
    except: pass

@app.route('/api/sync', methods=['POST'])
@token_required
def sync_now(curr_user_mat, role):
    migrated, errs = perform_sync_for_user(curr_user_mat)
    return jsonify({'message': f'Sincronização concluída. {migrated} registros enviados.', 'migrated': migrated, 'errors': errs}), 200

def perform_sync_for_user(user_matricula):
    """
    Core sync logic that can be called via API or background thread.
    Returns (migrated_count, errors_list)
    """
    lock = get_user_sync_lock(user_matricula)
    if not lock.acquire(blocking=False):
        print(f"DEBUG: Sync already in progress for {user_matricula}. Skipping redundant run.")
        return 0, ["Sync already in progress"]

    try:
        migrated = 0
        errs = []
        
        # 1. Local-only move: OfflineQueue -> Local Mirror (TimeRecords)
        # This is always done first to empty the frontend-style queue into the local mirror.
        try:
            lconn = sqlite3.connect(sqlite_path)
            lconn.row_factory = sqlite3.Row
            ensure_sqlite_schema(lconn)
            lcur = lconn.cursor()
            
            # Fetch pending from Queue
            lcur.execute("SELECT * FROM OfflineQueue WHERE matricula = ? ORDER BY timestamp ASC", (user_matricula,))
            q_rows = lcur.fetchall()
            
            if q_rows:
                # Existing local signatures to avoid double local moves
                lcur.execute("SELECT record_type, timestamp, transaction_id FROM TimeRecords WHERE matricula = ?", (user_matricula,))
                local_sigs = set()
                for lr in lcur.fetchall():
                    ts_val = rf(lr, 'timestamp')
                    ts_str = str(ts_val).split('.')[0]
                    tx_id = rf(lr, 'transaction_id')
                    local_sigs.add((rf(lr, 'record_type'), ts_str))
                    if tx_id: local_sigs.add(str(tx_id))
                
                for qr in q_rows:
                    ts_val = rf(qr, 'timestamp')
                    ts_str = str(ts_val).split('.')[0]
                    tx_id = rf(qr, 'transaction_id')
                    tx_id_str = str(tx_id) if tx_id else None
                    
                    is_dupe = (rf(qr, 'record_type'), ts_str) in local_sigs or (tx_id_str and tx_id_str in local_sigs)
                    
                    # ATOMIC MOVE: Only delete from OfflineQueue if it's already in local mirror or successfully inserted now
                    can_delete = False
                    if is_dupe:
                        can_delete = True
                    else:
                        try:
                            lcur.execute("""
                                INSERT INTO TimeRecords (user_id, matricula, user_name, record_type, timestamp, neighborhood, city, latitude, longitude, accuracy, full_address, transaction_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (rf(qr,'user_id'), rf(qr,'matricula'), rf(qr,'user_name'), rf(qr,'record_type'), rf(qr,'timestamp'), 
                                  rf(qr,'neighborhood'), rf(qr,'city'), rf(qr,'latitude'), rf(qr,'longitude'), rf(qr,'accuracy'), rf(qr,'full_address'), tx_id))
                            can_delete = True
                        except Exception as ins_err:
                            errs.append(f"Local Insert failed for {tx_id}: {ins_err}")
                    
                    if can_delete:
                        lcur.execute("DELETE FROM OfflineQueue WHERE id = ?", (rf(qr, 'id'),))
                lconn.commit()
            lconn.close()
        except Exception as e:
            errs.append(f"Local move error: {e}")

        # 2. Remote Sync: Local Mirror -> SQL Server
        # Only if SQL Server is configured and reachable.
        remote_conn = get_remote_db_connection()
        if remote_conn:
            try:
                rcur = remote_conn.cursor()
                sph = get_ph(remote_conn)
                is_pymssql = hasattr(remote_conn, 'as_dict')
                
                # Ensure remote schema
                print(f"DEBUG: Checking remote schema for {user_matricula}...")
                try:
                    for col, col_type in [
                        ("latitude", "FLOAT"), ("longitude", "FLOAT"), ("accuracy", "FLOAT"), 
                        ("full_address", "NVARCHAR(MAX)"), ("transaction_id", "NVARCHAR(100)"),
                        ("matricula", "NVARCHAR(50)"), ("user_name", "NVARCHAR(200)"),
                        ("neighborhood", "NVARCHAR(200)"), ("city", "NVARCHAR(200)")
                    ]:
                        try: 
                            rcur.execute(f"ALTER TABLE TimeRecords ADD {col} {col_type}")
                            if not is_pymssql and not getattr(remote_conn, 'autocommit', False): 
                                remote_conn.commit()
                        except: pass
                    print("DEBUG: Remote schema check complete.")
                except Exception as sch_err:
                    print(f"DEBUG: Schema check error: {sch_err}")

                # Fetch user info from Remote
                sql_user_id, user_name = get_user_info_by_matricula(user_matricula, remote_conn)
                print(f"DEBUG: Remote user fetch for {user_matricula}: ID={sql_user_id}, Name={user_name}")
                
                # v6.7: Sync user to remote if missing
                if not sql_user_id:
                    print(f"DEBUG: User {user_matricula} not found on remote. Attempting to sync user record...")
                    try:
                        ltmp_conn = sqlite3.connect(sqlite_path); ltmp_conn.row_factory = sqlite3.Row
                        ucur = ltmp_conn.cursor()
                        ucur.execute("SELECT * FROM Users WHERE matricula = ?", (str(user_matricula),))
                        u_data = ucur.fetchone()
                        if u_data:
                            # Use matricula as ID if numeric, else let it be auto (if possible)
                            try: fallback_id = int(str(user_matricula).strip())
                            except: fallback_id = None
                            
                            # SQL Server INSERT for Users
                            try:
                                # Ensure remote Users table has matricula if missing
                                try: rcur.execute("ALTER TABLE Users ADD matricula NVARCHAR(50)")
                                except: pass
                                if not is_pymssql and not getattr(remote_conn, 'autocommit', False): remote_conn.commit()

                                # Try inserting with explicit ID if it's numeric and we have identity insert maybe? 
                                # Simpler: just insert and let remote handle ID, we use matricula for mapping mostly.
                                rcur.execute(f"INSERT INTO Users (name, matricula, password, role) VALUES ({sph}, {sph}, {sph}, {sph})", 
                                             (rf(u_data, 'name'), str(user_matricula), rf(u_data, 'password'), rf(u_data, 'role')))
                                if not is_pymssql and not getattr(remote_conn, 'autocommit', False): remote_conn.commit()
                                print(f"DEBUG: Successfully synced user {user_matricula} to remote.")
                                # Re-fetch ID
                                sql_user_id, user_name = get_user_info_by_matricula(user_matricula, remote_conn)
                            except Exception as u_ins_err:
                                print(f"DEBUG: Could not insert user to remote: {u_ins_err}")
                        ltmp_conn.close()
                    except Exception as u_sync_err:
                        print(f"DEBUG: User sync logic failed: {u_sync_err}")

                # v6.6: Improved Fallback - use matricula as integer ID if remote fetch still fails
                if not user_name:
                    try:
                        ltmp_conn = sqlite3.connect(sqlite_path)
                        ltmp_conn.row_factory = sqlite3.Row
                        _, local_user_name = get_user_info_by_matricula(user_matricula, ltmp_conn)
                        ltmp_conn.close()
                        if local_user_name:
                            user_name = local_user_name
                            print(f"DEBUG: Using local info fallback for {user_matricula}: {user_name}")
                        
                        if not sql_user_id:
                            try:
                                # Many systems use matricula as the primary/external ID
                                sql_user_id = int(str(user_matricula).strip())
                                print(f"DEBUG: Using matricula as numeric fallback for user_id: {sql_user_id}")
                            except:
                                sql_user_id = 0
                                print("DEBUG: Using 0 as ultimate user_id fallback.")
                    except Exception as f_err:
                        print(f"DEBUG: Fallback error: {f_err}")
                
                # Build remote signatures
                existing_sigs = set()
                # Use a small check range for speed, but deep enough to catch recent dupes (last 90 days)
                # SQL Server specific syntax for DATEADD if not sqlite
                nolock = "WITH (NOLOCK)" if not is_pymssql else ""
                rcur.execute(f"SELECT record_type, timestamp, transaction_id FROM TimeRecords {nolock} WHERE matricula = {sph} AND timestamp >= DATEADD(day, -90, GETDATE())", (user_matricula,))
                for row in rcur.fetchall():
                    ts_val = rf(row, 'timestamp')
                    ts_str = str(ts_val).split('.')[0]
                    tx_id = rf(row, 'transaction_id')
                    existing_sigs.add((rf(row, 'record_type'), ts_str))
                    if tx_id: existing_sigs.add(str(tx_id))
                
                # Fetch from local mirror
                lconn = sqlite3.connect(sqlite_path)
                lconn.row_factory = sqlite3.Row
                lcur = lconn.cursor()
                lcur.execute("SELECT * FROM TimeRecords WHERE matricula = ? AND timestamp >= date('now', '-90 days')", (str(user_matricula),))
                mirror_rows = lcur.fetchall()
                print(f"DEBUG: Local mirror rows found for {user_matricula}: {len(mirror_rows)}")
                
                for mr in mirror_rows:
                    ts_val = rf(mr, 'timestamp')
                    # Standardize
                    ts_dt = ts_val
                    if isinstance(ts_val, str):
                        try:
                            if '.' in ts_val: ts_dt = datetime.datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S.%f")
                            else: ts_dt = datetime.datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S")
                        except: pass
                    if isinstance(ts_dt, datetime.datetime): ts_dt = ts_dt.replace(microsecond=0)
                    cmp_ts = str(ts_dt).split('.')[0]
                    tx_id = rf(mr, 'transaction_id')
                    tx_id_str = str(tx_id) if tx_id else None
                    
                    if (rf(mr, 'record_type'), cmp_ts) not in existing_sigs and (not tx_id_str or tx_id_str not in existing_sigs):
                        try:
                            rcur.execute(f"""
                                INSERT INTO TimeRecords (user_id, matricula, user_name, record_type, timestamp, neighborhood, city, latitude, longitude, accuracy, full_address, transaction_id)
                                VALUES ({sph}, {sph}, {sph}, {sph}, {sph}, {sph}, {sph}, {sph}, {sph}, {sph}, {sph}, {sph})
                            """, (sql_user_id, str(user_matricula), user_name, rf(mr, 'record_type'), ts_dt,
                                  rf(mr, 'neighborhood'), rf(mr, 'city'), rf(mr, 'latitude'), rf(mr, 'longitude'), 
                                  rf(mr, 'accuracy'), rf(mr, 'full_address'), tx_id))
                            migrated += 1
                            print(f"DEBUG: Successfully synced record {tx_id} for {user_matricula}")
                        except Exception as e:
                            print(f"DEBUG: SQL Insert error for {tx_id}: {e}")
                            errs.append(f"SQL Insert error: {e}")
                
                if not is_pymssql and not getattr(remote_conn, 'autocommit', False): 
                    remote_conn.commit()
                remote_conn.close()
                lconn.close()
            except Exception as e:
                errs.append(f"Remote sync error: {e}")
        
        return migrated, errs
    finally:
        lock.release()

def auto_sync_all():
    """Finds all users with pending items and syncs them."""
    print("DEBUG: Starting automatic background synchronization...")
    try:
        sconn = sqlite3.connect(sqlite_path)
        sconn.row_factory = sqlite3.Row
        scur = sconn.cursor()
        # Find all distinct matriculas and user_ids in the queue
        scur.execute("SELECT DISTINCT matricula, user_id FROM OfflineQueue")
        rows = scur.fetchall()
        
        synced_users = set()
        total_migrated = 0
        
        for r in rows:
            m = rf(r, 'matricula')
            uid = rf(r, 'user_id')
            
            # If matricula is missing, try to find it via user_id
            if not m or m == '':
                scur.execute("SELECT matricula FROM Users WHERE id = ? OR matricula = ?", (uid, str(uid)))
                u_row = scur.fetchone()
                m = rf(u_row, 'matricula') if u_row else None
            
            if m and m not in synced_users:
                print(f"DEBUG: Auto-syncing for matricula: {m}")
                migrated, errs = perform_sync_for_user(m)
                total_migrated += migrated
                synced_users.add(m)
        
        sconn.close()
        if total_migrated > 0:
            print(f"DEBUG: Automatic sync complete. {total_migrated} records synchronized.")
    except Exception as e:
        print(f"DEBUG: Auto-sync error: {e}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5005'))
    ensure_default_admin()
    migrate_local_data()
    start_health_check()
    app.run(host='0.0.0.0', debug=False, port=port)
