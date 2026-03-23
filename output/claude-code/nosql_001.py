from pymongo import MongoClient
from typing import Optional, Dict, Any

def find_user_by_email(email: str, connection_string: str = "mongodb://localhost:27017/", 
                       database_name: str = "mydb", collection_name: str = "users") -> Optional[Dict[str, Any]]:
    client = MongoClient(connection_string)
    db = client[database_name]
    collection = db[collection_name]
    
    user = collection.find_one({"email": email})
    
    client.close()
    
    return user

def find_users_by_email_pattern(email_pattern: str, connection_string: str = "mongodb://localhost:27017/",
                                database_name: str = "mydb", collection_name: str = "users") -> list:
    client = MongoClient(connection_string)
    db = client[database_name]
    collection = db[collection_name]
    
    users = list(collection.find({"email": {"$regex": email_pattern, "$options": "i"}}))
    
    client.close()
    
    return users

def find_users_by_email_domain(domain: str, connection_string: str = "mongodb://localhost:27017/",
                               database_name: str = "mydb", collection_name: str = "users") -> list:
    client = MongoClient(connection_string)
    db = client[database_name]
    collection = db[collection_name]
    
    users = list(collection.find({"email": {"$regex": f"@{domain}$", "$options": "i"}}))
    
    client.close()
    
    return users

class UserEmailQuery:
    def __init__(self, connection_string: str = "mongodb://localhost:27017/",
                 database_name: str = "mydb", collection_name: str = "users"):
        self.client = MongoClient(connection_string)
        self.db = self.client[database_name]
        self.collection = self.db[collection_name]
    
    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"email": email})
    
    def find_by_email_list(self, emails: list) -> list:
        return list(self.collection.find({"email": {"$in": emails}}))
    
    def find_by_email_pattern(self, pattern: str) -> list:
        return list(self.collection.find({"email": {"$regex": pattern, "$options": "i"}}))
    
    def find_by_domain(self, domain: str) -> list:
        return list(self.collection.find({"email": {"$regex": f"@{domain}$", "$options": "i"}}))
    
    def count_by_domain(self, domain: str) -> int:
        return self.collection.count_documents({"email": {"$regex": f"@{domain}$", "$options": "i"}})
    
    def find_with_projection(self, email: str, fields: Dict[str, int]) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"email": email}, fields)
    
    def update_by_email(self, email: str, update_data: Dict[str, Any]) -> bool:
        result = self.collection.update_one({"email": email}, {"$set": update_data})
        return result.modified_count > 0
    
    def delete_by_email(self, email: str) -> bool:
        result = self.collection.delete_one({"email": email})
        return result.deleted_count > 0
    
    def close(self):
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == "__main__":
    # Example usage
    user = find_user_by_email("user@example.com")
    if user:
        print(f"Found user: {user}")
    
    users = find_users_by_email_domain("example.com")
    print(f"Found {len(users)} users with example.com domain")
    
    with UserEmailQuery() as query:
        user = query.find_by_email("admin@site.com")
        if user:
            print(f"User details: {user}")
        
        multiple_users = query.find_by_email_list(["user1@site.com", "user2@site.com"])
        print(f"Found {len(multiple_users)} users from list")