def is_strong_password(value):
    if not isinstance(value, str) or len(value) < 12 or len(value) > 128:
        return False
    has_upper = any(c.isupper() for c in value)
    has_lower = any(c.islower() for c in value)
    has_digit = any(c.isdigit() for c in value)
    has_symbol = any(not c.isalnum() for c in value)
    return has_upper and has_lower and has_digit and has_symbol