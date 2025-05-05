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
from langchain_utils import get_langchain_sql_chain
import logging
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, 
     supports_credentials=True,
     origins=[
         "http://localhost:3000",  # Frontend dev server
         "https://your-frontend.onrender.com",  # If frontend deploys later
         "https://your-backend.onrender.com"     # Render backend
     ])

# Configuration
app.config['UPLOAD_FOLDER'] = 'user_uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# INIT
init_user_db()
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"error": "Email and password are required"}), 400
            
        if register_user(data["email"], data["password"]):
            create_user_db(data["email"])
            return jsonify({"message": "Registered successfully"}), 200
        else:
            return jsonify({"error": "Email already exists"}), 400
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"error": "Email and password are required"}), 400
            
        if verify_user(data["email"], data["password"]):
            token = generate_token(data["email"])
            return jsonify({"token": token}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/upload-schema', methods=['POST'])
@login_required
def upload_schema(user):
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Unsupported file type. Please upload .csv or .xlsx'}), 400

        email = user['sub']
        safe_email = email.replace('@', '_at_')
        user_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_email)
        os.makedirs(user_path, exist_ok=True)

        filename = secure_filename(file.filename)
        file_path = os.path.join(user_path, filename)
        file.save(file_path)

        try:
            schema_sections = []
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
                schema_str = "📄 **data.csv**\n" + '\n'.join([f"{col}: {str(dtype)}" for col, dtype in df.dtypes.items()])
                schema_sections.append(schema_str)
            elif filename.endswith(('.xlsx', '.xls')):
                xl = pd.ExcelFile(file_path)
                for sheet in xl.sheet_names:
                    df = xl.parse(sheet)
                    section = f"📄 **{sheet}**\n" + '\n'.join([f"{col}: {str(dtype)}" for col, dtype in df.dtypes.items()])
                    schema_sections.append(section)

            full_schema = '\n\n'.join(schema_sections)
            return jsonify({
                'message': 'Schema uploaded and parsed successfully', 
                'schema': full_schema,
                'file_path': file_path
            }), 200

        except Exception as e:
            logger.error(f"File parsing error: {str(e)}")
            return jsonify({'error': f'Failed to parse file: {str(e)}'}), 500

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/schema', methods=['GET'])
@login_required
def get_schema(user):
    try:
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

            return jsonify({"schema": schema}), 200
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Schema retrieval error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/transcribe', methods=['POST'])
@login_required
def transcribe(user):
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio uploaded'}), 400

        user_id = user['sub']
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No selected audio file'}), 400

        safe_email = user_id.replace('@', '_at_')
        path = os.path.join(app.config['UPLOAD_FOLDER'], safe_email)
        os.makedirs(path, exist_ok=True)
        
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(path, filename)
        audio_file.save(filepath)

        text = transcribe_audio(filepath)
        return jsonify({'transcript': text, 'path': filepath}), 200

    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/generate-sql', methods=['POST'])
@login_required
def sql_gen(user):
    try:
        data = request.get_json()
        if not data or 'question' not in data or 'schema' not in data:
            return jsonify({'error': 'Question and schema are required'}), 400

        sql = generate_sql(data['question'], data['schema'])
        return jsonify({'sql': sql}), 200
    except Exception as e:
        logger.error(f"SQL generation error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/run-query', methods=['POST'])
@login_required
def run(user):
    try:
        data = request.get_json()
        if not data or 'sql' not in data:
            return jsonify({'error': 'SQL query is required'}), 400

        email = user['sub']
        sql = data['sql']
        result = execute_query(email, sql)
        return jsonify({'result': result}), 200
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/ask', methods=['POST'])
@login_required
def ask_query(user):
    try:
        data = request.get_json()
        question = data.get("question")
        if not question:
            return jsonify({"error": "Missing question"}), 400

        db_path = get_user_db_path(user["sub"])

        chain = get_langchain_sql_chain(db_path)
        response = chain.run(question)
        return jsonify({"answer": response}), 200
    except Exception as e:
        logger.error(f"Query answering error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)