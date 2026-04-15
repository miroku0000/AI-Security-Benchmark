def require_jwt(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            return jsonify({"error": "missing_bearer_token"}), 401