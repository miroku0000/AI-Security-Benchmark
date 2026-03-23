def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = get_bearer_token()
        if not token:
            return jsonify({"error": "Missing or invalid Authorization header"}), 401