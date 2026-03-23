from pymongo import MongoClient
from typing import Any, Dict, List


def find_users_by_email(
    connection_uri: str,
    database_name: str,
    collection_name: str,
    email: str,
) -> List[Dict[str, Any]]:
    client = MongoClient(connection_uri)
    try:
        collection = client[database_name][collection_name]
        cursor = collection.find({"email": email})
        return list(cursor)
    finally:
        client.close()


if __name__ == "__main__":
    import os

    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGODB_DB", "app")
    coll_name = os.environ.get("MONGODB_COLLECTION", "users")
    target_email = os.environ.get("USER_EMAIL", "user@example.com")

    users = find_users_by_email(uri, db_name, coll_name, target_email)
    for doc in users:
        print(doc)
