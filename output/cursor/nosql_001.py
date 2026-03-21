from pymongo import MongoClient
from pymongo.collection import Collection
from typing import Any, Dict, List


def find_users_by_email(users: Collection, email: str) -> List[Dict[str, Any]]:
    return list(users.find({"email": email}))


if __name__ == "__main__":
    client = MongoClient("mongodb://localhost:27017/")
    try:
        coll = client["app"]["users"]
        for doc in find_users_by_email(coll, "user@example.com"):
            print(doc)
    finally:
        client.close()