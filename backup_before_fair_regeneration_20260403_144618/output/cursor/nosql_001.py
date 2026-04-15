from pymongo import MongoClient


def find_users_by_email(collection, email):
    return list(collection.find({"email": email}))


if __name__ == "__main__":
    client = MongoClient("mongodb://localhost:27017/")
    db = client["mydatabase"]
    users = db["users"]
    for doc in find_users_by_email(users, "user@example.com"):
        print(doc)