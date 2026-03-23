def search_users_by_username(
    server_uri: str,
    bind_dn: str,
    bind_password: str,
    base_dn: str,
    username: str,
    user_attribute: str = "uid",
    attributes: Optional[List[str]] = None,
    use_ssl: bool = False,
) -> List[Dict[str, Any]]:
    if attributes is None:
        attributes = ["cn", "mail", user_attribute]