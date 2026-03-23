import jwt
import json
import base64
from datetime import datetime
import sys

def decode_jwt_debug(token, secret=None, verify=False):
    """Debug utility to decode and inspect JWT tokens"""
    
    # Split token into parts
    parts = token.split('.')
    if len(parts) != 3:
        print(f"Error: Invalid JWT format. Expected 3 parts, got {len(parts)}")
        return None
    
    # Decode header
    try:
        header_padding = parts[0] + '=' * (4 - len(parts[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_padding))
        print("\n=== JWT HEADER ===")
        print(json.dumps(header, indent=2))
    except Exception as e:
        print(f"Error decoding header: {e}")
        return None
    
    # Decode payload
    try:
        payload_padding = parts[1] + '=' * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_padding))
        print("\n=== JWT PAYLOAD ===")
        print(json.dumps(payload, indent=2))
        
        # Check standard claims
        print("\n=== STANDARD CLAIMS ===")
        if 'exp' in payload:
            exp_time = datetime.fromtimestamp(payload['exp'])
            is_expired = datetime.now() > exp_time
            print(f"Expires: {exp_time} ({'EXPIRED' if is_expired else 'VALID'})")
        
        if 'iat' in payload:
            iat_time = datetime.fromtimestamp(payload['iat'])
            print(f"Issued At: {iat_time}")
        
        if 'nbf' in payload:
            nbf_time = datetime.fromtimestamp(payload['nbf'])
            is_active = datetime.now() >= nbf_time
            print(f"Not Before: {nbf_time} ({'ACTIVE' if is_active else 'NOT YET ACTIVE'})")
        
        if 'iss' in payload:
            print(f"Issuer: {payload['iss']}")
        
        if 'sub' in payload:
            print(f"Subject: {payload['sub']}")
        
        if 'aud' in payload:
            print(f"Audience: {payload['aud']}")
        
        if 'jti' in payload:
            print(f"JWT ID: {payload['jti']}")
            
    except Exception as e:
        print(f"Error decoding payload: {e}")
        return None
    
    # Signature info
    print("\n=== SIGNATURE ===")
    print(f"Signature (base64url): {parts[2][:50]}..." if len(parts[2]) > 50 else f"Signature (base64url): {parts[2]}")
    print(f"Algorithm: {header.get('alg', 'Not specified')}")
    
    # Verify signature if secret provided
    if verify and secret:
        print("\n=== VERIFICATION ===")
        try:
            # Try different algorithms
            algorithms = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512']
            alg = header.get('alg', 'HS256')
            
            if alg in algorithms:
                decoded = jwt.decode(token, secret, algorithms=[alg], options={"verify_exp": False})
                print(f"✓ Signature verified with {alg}")
                
                # Check expiration separately
                if 'exp' in decoded:
                    try:
                        jwt.decode(token, secret, algorithms=[alg])
                        print("✓ Token is not expired")
                    except jwt.ExpiredSignatureError:
                        print("✗ Token is expired")
                    except Exception as e:
                        print(f"✗ Verification failed: {e}")
            else:
                print(f"✗ Unsupported algorithm: {alg}")
                
        except jwt.InvalidSignatureError:
            print("✗ Invalid signature")
        except jwt.DecodeError as e:
            print(f"✗ Decode error: {e}")
        except Exception as e:
            print(f"✗ Verification failed: {e}")
    elif verify:
        print("\n=== VERIFICATION ===")
        print("⚠ No secret provided, cannot verify signature")
    
    # Decode without verification for debugging
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        print(f"\nError in final decode: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("JWT Token Debug Utility")
        print("========================")
        print("\nUsage:")
        print("  python jwt_debug_utility.py <token> [secret]")
        print("\nExample:")
        print('  python jwt_debug_utility.py "eyJhbGc..." ')
        print('  python jwt_debug_utility.py "eyJhbGc..." "your-secret-key"')
        print("\nOptions:")
        print("  <token>   JWT token to decode and inspect")
        print("  [secret]  Optional secret key for signature verification")
        sys.exit(1)
    
    token = sys.argv[1]
    secret = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("JWT TOKEN DEBUGGER")
    print("==================")
    
    result = decode_jwt_debug(token, secret, verify=(secret is not None))
    
    if result:
        print("\n=== DECODED SUCCESSFULLY ===")
        print("Token contents accessible for debugging")
    else:
        print("\n=== DECODE FAILED ===")
        print("Check token format and try again")

if __name__ == "__main__":
    main()