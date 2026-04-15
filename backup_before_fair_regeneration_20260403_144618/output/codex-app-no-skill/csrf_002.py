def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id not in users:
            return jsonify({"error": "authentication_required"}), 401
        return fn(*args, **kwargs)