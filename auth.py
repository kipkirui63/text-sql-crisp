from flask import request, jsonify
from functools import wraps
from user import decode_token

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return jsonify({"error": "Missing token"}), 401

        user = decode_token(token)
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 403

        return f(user, *args, **kwargs)
    return decorated