import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import hashlib
import hmac
import secrets
from typing import Dict, Any, Optional

class DataEncryptor:
    def __init__(self, master_key: Optional[str] = None):
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = os.environ.get('ENCRYPTION_KEY', '').encode()
        
        if not self.master_key:
            raise ValueError("Encryption key not provided")
        
        self.salt = os.environ.get('ENCRYPTION_SALT', 'default_salt_change_in_production').encode()
        self._cipher = self._get_cipher()
    
    def _get_cipher(self) -> Fernet:
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def encrypt_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        encrypted_data = {}
        
        for field, value in data.items():
            if value is None:
                encrypted_data[field] = None
                continue
            
            str_value = str(value)
            encrypted_value = self._cipher.encrypt(str_value.encode())
            encrypted_data[field] = base64.b64encode(encrypted_value).decode('utf-8')
            
            hash_field = f"{field}_hash"
            encrypted_data[hash_field] = self._create_hmac(str_value)
        
        encrypted_data['iv'] = base64.b64encode(secrets.token_bytes(16)).decode('utf-8')
        
        return encrypted_data
    
    def decrypt_data(self, encrypted_data: Dict[str, str]) -> Dict[str, Any]:
        decrypted_data = {}
        
        for field, value in encrypted_data.items():
            if field.endswith('_hash') or field == 'iv':
                continue
            
            if value is None:
                decrypted_data[field] = None
                continue
            
            encrypted_value = base64.b64decode(value.encode('utf-8'))
            decrypted_value = self._cipher.decrypt(encrypted_value).decode('utf-8')
            
            hash_field = f"{field}_hash"
            if hash_field in encrypted_data:
                if not self._verify_hmac(decrypted_value, encrypted_data[hash_field]):
                    raise ValueError(f"Data integrity check failed for field: {field}")
            
            decrypted_data[field] = decrypted_value
        
        return decrypted_data
    
    def _create_hmac(self, data: str) -> str:
        h = hmac.new(self.master_key, data.encode(), hashlib.sha256)
        return base64.b64encode(h.digest()).decode('utf-8')
    
    def _verify_hmac(self, data: str, hmac_value: str) -> bool:
        expected_hmac = self._create_hmac(data)
        return hmac.compare_digest(expected_hmac, hmac_value)

def encrypt_user_data(user_data: Dict[str, Any], encryption_key: Optional[str] = None) -> Dict[str, str]:
    encryptor = DataEncryptor(encryption_key)
    return encryptor.encrypt_data(user_data)

def decrypt_user_data(encrypted_data: Dict[str, str], encryption_key: Optional[str] = None) -> Dict[str, Any]:
    encryptor = DataEncryptor(encryption_key)
    return encryptor.decrypt_data(encrypted_data)

def store_encrypted_data(user_data: Dict[str, Any], database_connection, table_name: str = 'users'):
    encrypted_data = encrypt_user_data(user_data)
    
    columns = ', '.join(encrypted_data.keys())
    placeholders = ', '.join(['%s'] * len(encrypted_data))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    
    cursor = database_connection.cursor()
    cursor.execute(query, list(encrypted_data.values()))
    database_connection.commit()
    
    return cursor.lastrowid

def retrieve_decrypted_data(user_id: int, database_connection, table_name: str = 'users') -> Dict[str, Any]:
    cursor = database_connection.cursor()
    cursor.execute(f"SELECT * FROM {table_name} WHERE id = %s", (user_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
    
    columns = [desc[0] for desc in cursor.description]
    encrypted_data = dict(zip(columns, row))
    
    encrypted_data.pop('id', None)
    
    return decrypt_user_data(encrypted_data)