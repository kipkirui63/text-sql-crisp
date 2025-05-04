from flask import Flask, request, jsonify
from flask_cors import CORS
from user import init_user_db, register_user, verify_user, generate_token
from auth import login_required
from whisper_utils import transcribe_audio
from gpt_utils import generate_sql
from db_utils import execute_query, create_user_db, get_user_db_path
import os
import sqlite3
import pandas as pd

app = Flask(__name__)
CORS(app, supports_credentials=True)

# INIT
init_user_db()
os.makedirs("user_uploads", exist_ok=True)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if register_user(data["email"], data["password"]):
        create_user_db(data["email"])
        return jsonify({"message": "Registered successfully"}), 200
    else:
        return jsonify({"error": "Email already exists"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if verify_user(data["email"], data["password"]):
        token = generate_token(data["email"])
        return jsonify({"token": token}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/upload-schema', methods=['POST'])
@login_required
def upload_schema(user):
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    try:
        import openpyxl  # Test if import works
    except ImportError:
        return jsonify({
            'error': "Server missing required Excel support. Please contact admin."
        }), 500

    user_id = user['sub']
    file = request.files['file']
    filename = file.filename
    user_path = f"user_uploads/{user_id}/"
    os.makedirs(user_path, exist_ok=True)

    file_path = os.path.join(user_path, filename)
    file.save(file_path)

    db_path = get_user_db_path(user_id)
    conn = sqlite3.connect(db_path)

    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path)
            table_name = os.path.splitext(filename)[0]
            df.to_sql(table_name, conn, if_exists='replace', index=False)
        elif filename.endswith(('.xls', '.xlsx')):
            # Use openpyxl explicitly for xlsx files
            excel = pd.ExcelFile(file_path, engine='openpyxl')
            for sheet_name in excel.sheet_names:
                df = excel.parse(sheet_name)
                df.to_sql(sheet_name, conn, if_exists='replace', index=False)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

    return jsonify({'message': 'Schema uploaded successfully'}), 200
@app.route('/schema', methods=['GET'])
@login_required
def get_schema(user):
    user_id = user['sub']
    db_path = get_user_db_path(user_id)

    if not os.path.exists(db_path):
        return jsonify({"error": "No schema found"}), 404

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        schema = {}

        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            schema[table_name] = columns

        return jsonify({"schema": schema})
    finally:
        conn.close()

@app.route('/transcribe', methods=['POST'])
@login_required
def transcribe(user):
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio uploaded'}), 400

    user_id = user['sub']
    audio_file = request.files['audio']
    path = f"user_uploads/{user_id}/"
    os.makedirs(path, exist_ok=True)
    filepath = os.path.join(path, audio_file.filename)
    audio_file.save(filepath)

    text = transcribe_audio(filepath)
    return jsonify({'transcript': text, 'path': filepath})

@app.route('/generate-sql', methods=['POST'])
@login_required
def sql_gen(user):
    data = request.get_json()
    sql = generate_sql(data['question'], data['schema'])
    return jsonify({'sql': sql})

@app.route('/run-query', methods=['POST'])
@login_required
def run(user):
    data = request.get_json()
    email = user['sub']
    sql = data['sql']
    result = execute_query(email, sql)
    return jsonify({'result': result})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
