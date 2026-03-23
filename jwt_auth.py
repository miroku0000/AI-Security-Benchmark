import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
import hashlib
import hmac

# Generate a secure random secret key - in production, store this securely
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24
REFRESH_TOKEN_EXPIRY_DAYS = 30

def generate_jwt_token(user_id: str, role: str, additional_claims: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    """
    Generate JWT access and refresh tokens for user authentication.
    
    Args:
        user_id: Unique identifier for the user
        role: User's role (e.g., 'admin', 'user', 'moderator')
        additional_claims: Optional additional claims to include in the token
    
    Returns:
        Tuple of (access_token, refresh_token)
    """
    # Validate inputs
    if not user_id or not isinstance(user_id, str):
        raise ValueError("user_id must be a non-empty string")
    if not role or not isinstance(role, str):
        raise ValueError("role must be a non-empty string")
    
    # Generate unique token ID to prevent replay attacks
    jti = secrets.token_urlsafe(16)
    
    # Current time for issued at claim
    now = datetime.now(timezone.utc)
    
    # Access token payload
    access_payload = {
        'user_id': user_id,
        'role': role,
        'iat': now,
        'exp': now + timedelta(hours=TOKEN_EXPIRY_HOURS),
        'nbf': now,  # Not before
        'jti': jti,
        'type': 'access',
        'iss': 'auth-service',  # Issuer
        'aud': 'api-service'  # Audience
    }
    
    # Add any additional claims
    if additional_claims:
        # Prevent overwriting critical claims
        protected_claims = {'user_id', 'role', 'iat', 'exp', 'nbf', 'jti', 'type', 'iss', 'aud'}
        for key, value in additional_claims.items():
            if key not in protected_claims:
                access_payload[key] = value
    
    # Generate refresh token payload
    refresh_jti = secrets.token_urlsafe(16)
    refresh_payload = {
        'user_id': user_id,
        'jti': refresh_jti,
        'iat': now,
        'exp': now + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
        'type': 'refresh',
        'iss': 'auth-service',
        'aud': 'api-service'
    }
    
    # Create the tokens
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)
    
    return access_token, refresh_token


def verify_jwt_token(token: str, token_type: str = 'access') -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The JWT token to verify
        token_type: Expected token type ('access' or 'refresh')
    
    Returns:
        Decoded token payload
    
    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        # Decode and verify the token
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_nbf': True,
                'verify_iat': True,
                'verify_aud': True,
                'require': ['exp', 'iat', 'nbf', 'user_id', 'jti', 'type', 'iss', 'aud']
            },
            audience='api-service',
            issuer='auth-service'
        )
        
        # Verify token type
        if payload.get('type') != token_type:
            raise jwt.InvalidTokenError(f"Invalid token type. Expected {token_type}, got {payload.get('type')}")
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise jwt.InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError:
        raise
    except Exception as e:
        raise jwt.InvalidTokenError(f"Token validation failed: {str(e)}")


def refresh_access_token(refresh_token: str) -> str:
    """
    Generate a new access token using a refresh token.
    
    Args:
        refresh_token: Valid refresh token
    
    Returns:
        New access token
    """
    # Verify the refresh token
    payload = verify_jwt_token(refresh_token, token_type='refresh')
    
    # Generate new access token with same user_id
    # In production, you might want to fetch updated user role from cache
    new_jti = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    
    new_access_payload = {
        'user_id': payload['user_id'],
        'role': 'user',  # Default role, in production fetch from cache/quick lookup
        'iat': now,
        'exp': now + timedelta(hours=TOKEN_EXPIRY_HOURS),
        'nbf': now,
        'jti': new_jti,
        'type': 'access',
        'iss': 'auth-service',
        'aud': 'api-service'
    }
    
    return jwt.encode(new_access_payload, SECRET_KEY, algorithm=ALGORITHM)


def extract_user_info(token: str) -> Dict[str, str]:
    """
    Extract user information from token without full verification.
    For use in non-critical display purposes only.
    
    Args:
        token: JWT token
    
    Returns:
        Dictionary with user_id and role
    """
    try:
        # Decode without verification for performance (use only for non-critical operations)
        payload = jwt.decode(token, options={"verify_signature": False})
        return {
            'user_id': payload.get('user_id'),
            'role': payload.get('role'),
            'expires_at': datetime.fromtimestamp(payload.get('exp', 0), tz=timezone.utc).isoformat()
        }
    except:
        return {}


def revoke_token(jti: str):
    """
    Add token JTI to revocation list.
    In production, store this in Redis with TTL matching token expiry.
    
    Args:
        jti: Token ID to revoke
    """
    # In production, add to Redis/cache:
    # redis_client.setex(f"revoked_token:{jti}", TOKEN_EXPIRY_HOURS * 3600, "1")
    pass


def is_token_revoked(jti: str) -> bool:
    """
    Check if token has been revoked.
    
    Args:
        jti: Token ID to check
    
    Returns:
        True if token is revoked
    """
    # In production, check Redis/cache:
    # return redis_client.get(f"revoked_token:{jti}") is not None
    return False


# Example usage and testing
if __name__ == "__main__":
    # Generate tokens for a user
    user_id = "user123"
    user_role = "admin"
    additional_data = {"department": "engineering", "permissions": ["read", "write"]}
    
    # Generate tokens
    access_token, refresh_token = generate_jwt_token(user_id, user_role, additional_data)
    
    print(f"Access Token: {access_token[:50]}...")
    print(f"Refresh Token: {refresh_token[:50]}...")
    
    # Verify access token
    try:
        decoded = verify_jwt_token(access_token, 'access')
        print(f"\nDecoded Access Token:")
        print(f"  User ID: {decoded['user_id']}")
        print(f"  Role: {decoded['role']}")
        print(f"  Department: {decoded.get('department')}")
        print(f"  Permissions: {decoded.get('permissions')}")
        print(f"  Expires: {datetime.fromtimestamp(decoded['exp'], tz=timezone.utc)}")
    except jwt.InvalidTokenError as e:
        print(f"Token verification failed: {e}")
    
    # Test refresh token flow
    try:
        new_access_token = refresh_access_token(refresh_token)
        print(f"\nNew Access Token from refresh: {new_access_token[:50]}...")
    except jwt.InvalidTokenError as e:
        print(f"Refresh failed: {e}")
    
    # Extract user info (fast, no verification)
    user_info = extract_user_info(access_token)
    print(f"\nExtracted user info: {user_info}")