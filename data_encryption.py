import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import json
from typing import Any, Dict, Optional


class DataEncryptor:
    def __init__(self, password: Optional[str] = None, salt: Optional[bytes] = None):
        if password is None:
            password = os.environ.get('ENCRYPTION_PASSWORD', 'default-secure-password-change-me')
        
        if salt is None:
            salt = os.environ.get('ENCRYPTION_SALT', b'stable-salt-value').encode() if isinstance(os.environ.get('ENCRYPTION_SALT', b'stable-salt-value'), str) else os.environ.get('ENCRYPTION_SALT', b'stable-salt-value')
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.cipher = Fernet(key)
    
    def encrypt_user_data(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        encrypted_data = {}
        
        for field, value in user_data.items():
            if value is not None:
                value_str = json.dumps(value) if not isinstance(value, str) else value
                encrypted_value = self.cipher.encrypt(value_str.encode())
                encrypted_data[field] = base64.urlsafe_b64encode(encrypted_value).decode('utf-8')
            else:
                encrypted_data[field] = None
        
        return encrypted_data
    
    def decrypt_user_data(self, encrypted_data: Dict[str, str]) -> Dict[str, Any]:
        decrypted_data = {}
        
        for field, encrypted_value in encrypted_data.items():
            if encrypted_value is not None:
                encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode('utf-8'))
                decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
                decrypted_str = decrypted_bytes.decode('utf-8')
                
                try:
                    decrypted_data[field] = json.loads(decrypted_str)
                except json.JSONDecodeError:
                    decrypted_data[field] = decrypted_str
            else:
                decrypted_data[field] = None
        
        return decrypted_data


def encrypt_sensitive_user_data(user_data: Dict[str, Any], password: Optional[str] = None, salt: Optional[bytes] = None) -> Dict[str, str]:
    encryptor = DataEncryptor(password, salt)
    return encryptor.encrypt_user_data(user_data)


def decrypt_sensitive_user_data(encrypted_data: Dict[str, str], password: Optional[str] = None, salt: Optional[bytes] = None) -> Dict[str, Any]:
    encryptor = DataEncryptor(password, salt)
    return encryptor.decrypt_user_data(encrypted_data)


def store_encrypted_user_to_database(user_data: Dict[str, Any], db_connection, table_name: str = 'users'):
    encrypted_data = encrypt_sensitive_user_data(user_data)
    
    columns = ', '.join(encrypted_data.keys())
    placeholders = ', '.join(['%s'] * len(encrypted_data))
    values = list(encrypted_data.values())
    
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    
    cursor = db_connection.cursor()
    cursor.execute(query, values)
    db_connection.commit()
    cursor.close()
    
    return encrypted_data


def retrieve_and_decrypt_user_from_database(user_id: str, db_connection, table_name: str = 'users', id_column: str = 'id') -> Dict[str, Any]:
    query = f"SELECT * FROM {table_name} WHERE {id_column} = %s"
    
    cursor = db_connection.cursor()
    cursor.execute(query, (user_id,))
    
    columns = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    cursor.close()
    
    if row:
        encrypted_data = dict(zip(columns, row))
        non_encrypted_fields = [id_column, 'created_at', 'updated_at']
        
        data_to_decrypt = {k: v for k, v in encrypted_data.items() if k not in non_encrypted_fields}
        decrypted_data = decrypt_sensitive_user_data(data_to_decrypt)
        
        for field in non_encrypted_fields:
            if field in encrypted_data:
                decrypted_data[field] = encrypted_data[field]
        
        return decrypted_data
    
    return None


if __name__ == "__main__":
    sample_user_data = {
        "username": "john_doe",
        "email": "john@example.com",
        "ssn": "123-45-6789",
        "credit_card": "4111111111111111",
        "phone": "+1-555-123-4567",
        "address": {
            "street": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zip": "10001"
        }
    }
    
    encrypted = encrypt_sensitive_user_data(sample_user_data)
    print("Encrypted data:", encrypted)
    
    decrypted = decrypt_sensitive_user_data(encrypted)
    print("Decrypted data:", decrypted)
    
    assert sample_user_data == decrypted
    print("Encryption and decryption successful!")