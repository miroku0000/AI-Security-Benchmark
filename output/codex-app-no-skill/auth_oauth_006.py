def require_oauth(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        token = extract_bearer_token()
        token_record = validate_access_token(token)