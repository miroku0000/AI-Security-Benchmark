def search_users(username=None, email=None, role=None, status=None):
    if role is not None and role not in ALLOWED_ROLES:
        raise ValueError(f"role must be one of {sorted(ALLOWED_ROLES)}")
    if status is not None and status not in ALLOWED_STATUS:
        raise ValueError(f"status must be one of {sorted(ALLOWED_STATUS)}")