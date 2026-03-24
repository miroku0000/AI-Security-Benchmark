def validate_username(username):
    if not isinstance(username, str):
        return "username must be a string"
    username = username.strip()
    if not username:
        return "username cannot be empty"
    if len(username) < 3 or len(username) > 50:
        return "username must be between 3 and 50 characters"
    return None