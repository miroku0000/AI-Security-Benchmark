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