def find_users_by_email(
    collection: Collection,
    email: str,
    case_insensitive: bool = False,
) -> List[Dict[str, Any]]:
    if case_insensitive:
        return list(
            collection.find(
                {
                    "email": {
                        "$regex": f"^{email}$",
                        "$options": "i",
                    }
                }
            )
        )
    return list(collection.find({"email": email}))