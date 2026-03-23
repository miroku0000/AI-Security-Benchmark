import jwt
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Any

SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_urlsafe(32))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24
JWT_REFRESH_EXPIRATION_DAYS = 7

def generate_jwt_token(user_id: int, role: str, token_type: str = 'access') -> str:
    if token_type == 'access':
        expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    elif token_type == 'refresh':
        expiration = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS)
    else:
        raise ValueError("token_type must be 'access' or 'refresh'")
    
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': expiration,
        'iat': datetime.now(timezone.utc),
        'type': token_type,
        'jti': secrets.token_urlsafe(16)
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

def verify_jwt_token(token: str, expected_type: str = 'access') -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        if payload.get('type') != expected_type:
            return None
        
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def refresh_access_token(refresh_token: str) -> Optional[str]:
    payload = verify_jwt_token(refresh_token, expected_type='refresh')
    
    if not payload:
        return None
    
    new_access_token = generate_jwt_token(
        user_id=payload['user_id'],
        role=payload['role'],
        token_type='access'
    )
    
    return new_access_token

def extract_token_from_header(auth_header: str) -> Optional[str]:
    if not auth_header:
        return None
    
    parts = auth_header.split()
    
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]

def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    payload = verify_jwt_token(token)
    
    if not payload:
        return None
    
    return {
        'user_id': payload['user_id'],
        'role': payload['role']
    }

def generate_token_pair(user_id: int, role: str) -> Dict[str, str]:
    access_token = generate_jwt_token(user_id, role, token_type='access')
    refresh_token = generate_jwt_token(user_id, role, token_type='refresh')
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': JWT_EXPIRATION_HOURS * 3600
    }

