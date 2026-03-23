def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id or user_id not in users:
            return jsonify({"error": "Unauthorized"}), 401
        return view(*args, **kwargs)