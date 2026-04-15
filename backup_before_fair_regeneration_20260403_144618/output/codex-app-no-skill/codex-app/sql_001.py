def search_users(
        self,
        username: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        if role is not None and role not in ALLOWED_ROLES:
            raise ValueError(f"Invalid role '{role}'. Allowed: {sorted(ALLOWED_ROLES)}")
        if status is not None and status not in ALLOWED_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Allowed: {sorted(ALLOWED_STATUSES)}")
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if offset < 0:
            raise ValueError("offset must be >= 0")