## ✅ FULL BACKEND FILE: `app.py`
from flask import Flask, request, jsonify
from flask_cors import CORS
from user import init_user_db, register_user, verify_user, generate_token
from auth import login_required
from whisper_utils import transcribe_audio
from gpt_utils import generate_sql
from db_utils import execute_query, create_user_db
import os

app = Flask(__name__)
CORS(app)

# INIT
init_user_db()
os.makedirs("user_uploads", exist_ok=True)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if register_user(data["email"], data["password"]):
        create_user_db(data["email"])  # Create empty SQLite for this user
        return jsonify({"message": "Registered successfully"}), 200
    else:
        return jsonify({"error": "Email already exists"}), 400
    

@app.route('/upload-schema', methods=['POST'])
@login_required
def upload_schema(user):
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    user_id = user['sub']
    file = request.files['file']
    filename = file.filename
    user_path = f"user_uploads/{user_id}/"
    os.makedirs(user_path, exist_ok=True)

    file_path = os.path.join(user_path, filename)
    file.save(file_path)

    return jsonify({'message': 'Schema uploaded successfully', 'path': file_path})




@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if verify_user(data["email"], data["password"]):
        token = generate_token(data["email"])
        return jsonify({"token": token}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

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
