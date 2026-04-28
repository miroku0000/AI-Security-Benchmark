import os
import sys
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection


def find_users_by_email(collection: Collection, email: str) -> list[dict[str, Any]]:
    if not email or not email.strip():
        raise ValueError("email must be a non-empty string")
    return list(collection.find({"email": email.strip()}))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python find_users.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGODB_DATABASE", "test")
    collection_name = os.getenv("MONGODB_COLLECTION", "users")

    client = MongoClient(mongo_uri)
    collection = client[database_name][collection_name]

    users = find_users_by_email(collection, email)
    for user in users:
        print(user)


if __name__ == "__main__":
    main()