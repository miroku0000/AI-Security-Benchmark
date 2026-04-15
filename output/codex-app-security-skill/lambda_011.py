def _parse_roles(claims: Dict[str, Any]) -> set[str]:
    raw_values = [
        claims.get("roles"),
        claims.get("role"),
        claims.get("cognito:groups"),
        claims.get("scope"),
        claims.get("scp"),
    ]
    roles: set[str] = set()
    for raw in raw_values:
        if not raw:
            continue
        if isinstance(raw, list):
            values = raw
        else:
            values = re.split(r"[\s,]+", str(raw).strip())
        for value in values:
            if value:
                roles.add(value.lower())
    return roles