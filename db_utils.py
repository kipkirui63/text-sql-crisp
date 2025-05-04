import sqlite3
import os

def get_user_db_path(email):
    safe_email = email.replace("@", "_at_").replace(".", "_dot_")
    return f"user_uploads/{safe_email}/user_data.db"

def create_user_db(email):
    db_path = get_user_db_path(email)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.commit()
        conn.close()

def execute_query(email, sql):
    db_path = get_user_db_path(email)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        conn.commit()
        return {"columns": columns, "rows": rows}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

def fetch_schema(email):
    db_path = get_user_db_path(email)
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        schema = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            schema[table_name] = [col[1] for col in columns] 
        return schema
    finally:
        conn.close()
