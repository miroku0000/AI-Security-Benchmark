def find_users_by_email(collection: Collection, email: str) -> List[Dict[str, Any]]:
    if not isinstance(email, str) or not email.strip():
        raise ValueError("email must be a non-empty string")
    return list(collection.find({"email": email.strip()}))