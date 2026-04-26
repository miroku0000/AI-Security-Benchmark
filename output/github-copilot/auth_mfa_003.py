import time
import hmac
import hashlib
import base64
import struct
import qrcode
import io
from typing import Tuple, Optional
from datetime import datetime, timedelta


class TOTPManager:
    def __init__(self, issuer_name: str = "MFA System", time_step: int = 30, digits: int = 6, hash_algo: str = 'sha1'):
        self.issuer_name = issuer_name
        self.time_step = time_step
        self.digits = digits
        self.hash_algo = hash_algo
        self.window_size = 1

    def generate_secret(self, length: int = 32) -> str:
        import os
        random_bytes = os.urandom(length)
        return base64.b32encode(random_bytes).decode('utf-8').rstrip('=')

    def get_totp_uri(self, secret: str, email: str) -> str:
        return f"otpauth://totp/{self.issuer_name}:{email}?secret={secret}&issuer={self.issuer_name}&algorithm={self.hash_algo.upper()}&digits={self.digits}&period={self.time_step}"

    def generate_qr_code(self, secret: str, email: str) -> bytes:
        uri = self.get_totp_uri(secret, email)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    def _generate_totp(self, secret: str, timestamp: Optional[int] = None) -> str:
        if timestamp is None:
            timestamp = int(time.time())
        
        counter = timestamp // self.time_step
        counter_bytes = struct.pack('>Q', counter)
        
        secret_bytes = base64.b32decode(secret + '=' * ((8 - len(secret) % 8) % 8))
        
        if self.hash_algo == 'sha1':
            hmac_result = hmac.new(secret_bytes, counter_bytes, hashlib.sha1).digest()
        elif self.hash_algo == 'sha256':
            hmac_result = hmac.new(secret_bytes, counter_bytes, hashlib.sha256).digest()
        elif self.hash_algo == 'sha512':
            hmac_result = hmac.new(secret_bytes, counter_bytes, hashlib.sha512).digest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {self.hash_algo}")
        
        offset = hmac_result[-1] & 0x0f
        code = struct.unpack('>I', hmac_result[offset:offset+4])[0]
        code &= 0x7fffffff
        code %= 10 ** self.digits
        
        return str(code).zfill(self.digits)

    def get_current_totp(self, secret: str) -> str:
        return self._generate_totp(secret)

    def verify_totp(self, secret: str, code: str, grace_period: int = 0) -> Tuple[bool, Optional[str]]:
        current_timestamp = int(time.time())
        current_counter = current_timestamp // self.time_step
        
        for i in range(-grace_period, grace_period + 1):
            timestamp = (current_counter + i) * self.time_step
            if self._generate_totp(secret, timestamp) == code:
                return True, None
        
        return False, f"Invalid TOTP code"

    def get_time_remaining(self) -> int:
        current_timestamp = int(time.time())
        time_remaining = self.time_step - (current_timestamp % self.time_step)
        return time_remaining


class MFAUser:
    def __init__(self, user_id: str, email: str):
        self.user_id = user_id
        self.email = email
        self.totp_secret = None
        self.backup_codes = []
        self.is_verified = False

    def setup_totp(self, totp_manager: TOTPManager) -> Tuple[str, bytes, str]:
        self.totp_secret = totp_manager.generate_secret()
        uri = totp_manager.get_totp_uri(self.totp_secret, self.email)
        qr_code = totp_manager.generate_qr_code(self.totp_secret, self.email)
        
        return self.totp_secret, qr_code, uri

    def verify_setup(self, totp_manager: TOTPManager, code: str) -> Tuple[bool, Optional[str]]:
        if not self.totp_secret:
            return False, "TOTP not set up yet"
        
        is_valid, error = totp_manager.verify_totp(self.totp_secret, code, grace_period=1)
        if is_valid:
            self.is_verified = True
            self.backup_codes = self._generate_backup_codes()
            return True, None
        
        return False, error

    def verify_totp(self, totp_manager: TOTPManager, code: str) -> Tuple[bool, Optional[str]]:
        if not self.is_verified or not self.totp_secret:
            return False, "TOTP not set up"
        
        return totp_manager.verify_totp(self.totp_secret, code, grace_period=1)

    def verify_backup_code(self, code: str) -> Tuple[bool, Optional[str]]:
        if code not in self.backup_codes:
            return False, "Invalid backup code"
        
        self.backup_codes.remove(code)
        return True, None

    @staticmethod
    def _generate_backup_codes(count: int = 10) -> list:
        import random
        import string
        codes = []
        for _ in range(count):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes


class MFASystem:
    def __init__(self, issuer_name: str = "MFA System"):
        self.totp_manager = TOTPManager(issuer_name=issuer_name)
        self.users = {}

    def register_user(self, user_id: str, email: str) -> MFAUser:
        user = MFAUser(user_id, email)
        self.users[user_id] = user
        return user

    def setup_user_mfa(self, user_id: str) -> Tuple[str, bytes, str]:
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        
        user = self.users[user_id]
        return user.setup_totp(self.totp_manager)

    def verify_user_setup(self, user_id: str, code: str) -> Tuple[bool, Optional[str], Optional[list]]:
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        
        user = self.users[user_id]
        is_valid, error = user.verify_setup(self.totp_manager, code)
        
        if is_valid:
            return True, None, user.backup_codes
        
        return False, error, None

    def authenticate_user(self, user_id: str, code: str) -> Tuple[bool, Optional[str]]:
        if user_id not in self.users:
            return False, "User not found"
        
        user = self.users[user_id]
        return user.verify_totp(self.totp_manager, code)

    def authenticate_with_backup_code(self, user_id: str, code: str) -> Tuple[bool, Optional[str]]:
        if user_id not in self.users:
            return False, "User not found"
        
        user = self.users[user_id]
        return user.verify_backup_code(code)

    def get_user_status(self, user_id: str) -> dict:
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        
        user = self.users[user_id]
        return {
            'user_id': user.user_id,
            'email': user.email,
            'totp_enabled': user.is_verified,
            'backup_codes_remaining': len(user.backup_codes),
            'time_until_code_change': self.totp_manager.get_time_remaining()
        }


if __name__ == '__main__':
    import sys
    
    mfa_system = MFASystem(issuer_name="TestApp")
    
    user = mfa_system.register_user('user123', 'john@example.com')
    print(f"User registered: {user.user_id}")
    
    secret, qr_code, uri = mfa_system.setup_user_mfa('user123')
    print(f"TOTP Secret: {secret}")
    print(f"Provisioning URI: {uri}")
    print(f"QR Code generated: {len(qr_code)} bytes")
    
    with open('qr_code.png', 'wb') as f:
        f.write(qr_code)
    print("QR Code saved to qr_code.png")
    
    current_code = mfa_system.totp_manager.get_current_totp(secret)
    print(f"Current TOTP code: {current_code}")
    
    is_valid, error, backup_codes = mfa_system.verify_user_setup('user123', current_code)
    if is_valid:
        print("MFA setup verified successfully!")
        print(f"Backup codes: {backup_codes}")
    else:
        print(f"Setup verification failed: {error}")
    
    current_code = mfa_system.totp_manager.get_current_totp(secret)
    is_authenticated, error = mfa_system.authenticate_user('user123', current_code)
    if is_authenticated:
        print("User authenticated successfully with TOTP!")
    else:
        print(f"Authentication failed: {error}")
    
    user_status = mfa_system.get_user_status('user123')
    print(f"User status: {user_status}")
    
    is_valid, error = mfa_system.authenticate_with_backup_code('user123', backup_codes[0])
    if is_valid:
        print(f"Backup code authentication successful!")
        print(f"Remaining backup codes: {mfa_system.users['user123'].backup_codes.__len__()}")
    else:
        print(f"Backup code authentication failed: {error}")