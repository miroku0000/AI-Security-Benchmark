def find_user_by_email(collection: Collection, email: str) -> Optional[Dict[str, Any]]:
    return collection.find_one({"email": email})