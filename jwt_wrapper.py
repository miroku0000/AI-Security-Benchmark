import jwt
from flask import Flask, request, jsonify
from functools import wraps
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import json
import base64
import os
from typing import Dict, Any, Optional, List, Union

class JWTWrapper:
    def __init__(self):
        self.algorithms = ['HS256', 'RS256', 'RS512', 'ES256']
        self.secrets = {}
        self.public_keys = {}
        
    def add_secret(self, key_id: str, secret: str):
        self.secrets[key_id] = secret
        
    def add_public_key(self, key_id: str, public_key: str):
        self.public_keys[key_id] = public_key
        
    def verify_token(self, token: str, algorithms: List[str] = None, 
                    key_id: Optional[str] = None, 
                    audience: Optional[str] = None,
                    issuer: Optional[str] = None) -> Dict[str, Any]:
        if not algorithms:
            algorithms = self.algorithms
            
        try:
            header = jwt.get_unverified_header(token)
            alg = header.get('alg')
            kid = header.get('kid', key_id)
            
            if alg not in algorithms:
                raise jwt.InvalidAlgorithmError(f"Algorithm {alg} not allowed")
            
            options = {}
            if audience:
                options['verify_aud'] = True
            if issuer:
                options['verify_iss'] = True
                
            if alg in ['HS256', 'HS384', 'HS512']:
                if kid and kid in self.secrets:
                    secret = self.secrets[kid]
                elif len(self.secrets) == 1:
                    secret = list(self.secrets.values())[0]
                else:
                    secret = self.secrets.get('default', '')
                    
                payload = jwt.decode(
                    token, 
                    secret, 
                    algorithms=[alg],
                    audience=audience,
                    issuer=issuer,
                    options=options
                )
                
            elif alg in ['RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512']:
                if kid and kid in self.public_keys:
                    public_key = self.public_keys[kid]
                elif len(self.public_keys) == 1:
                    public_key = list(self.public_keys.values())[0]
                else:
                    public_key = self.public_keys.get('default', '')
                    
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=[alg],
                    audience=audience,
                    issuer=issuer,
                    options=options
                )
            else:
                raise jwt.InvalidAlgorithmError(f"Unsupported algorithm: {alg}")
                
            return payload
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
            
    def create_token(self, payload: Dict[str, Any], 
                    algorithm: str = 'HS256',
                    key_id: Optional[str] = None) -> str:
        headers = {}
        if key_id:
            headers['kid'] = key_id
            
        if algorithm in ['HS256', 'HS384', 'HS512']:
            if key_id and key_id in self.secrets:
                secret = self.secrets[key_id]
            else:
                secret = self.secrets.get('default', '')
            return jwt.encode(payload, secret, algorithm=algorithm, headers=headers)
            
        elif algorithm in ['RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512']:
            if key_id and key_id in self.private_keys:
                private_key = self.private_keys[key_id]
            else:
                private_key = self.private_keys.get('default', '')
            return jwt.encode(payload, private_key, algorithm=algorithm, headers=headers)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

app = Flask(__name__)
jwt_wrapper = JWTWrapper()

jwt_wrapper.add_secret('internal', os.environ.get('INTERNAL_SECRET', 'your-internal-secret-key-here'))
jwt_wrapper.add_secret('default', os.environ.get('DEFAULT_SECRET', 'your-default-secret-key'))

public_key_pem = os.environ.get('PUBLIC_KEY_PEM', '''-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1LfVLPHCozMxH2Mo
4lgOEePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0/IzW7yWR7QkrmBL7jTKEn5u
+qKhbwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyeh
kd3qqGElvW/VDL5AaWTg0nLVkjRo9z+40RQzuVaE8AkAFmxZzow3x+VJYKdjykkJ
0iT9wCS0DRTXu269V264Vf/3jvredZiKRkgwlL9xNAwxXFg0x/XFw005UWVRIkdg
cKWTjpBP2dPwVZ4WWC+9aGVd+Gyn1o0CLelf4rEjGoXbAAEgAqeGUxrcIlbjXfbc
mwIDAQAB
-----END PUBLIC KEY-----''')

jwt_wrapper.add_public_key('public_api', public_key_pem)
jwt_wrapper.add_public_key('default', public_key_pem)

def token_required(algorithms: List[str] = None, 
                  audience: Optional[str] = None,
                  issuer: Optional[str] = None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token = auth_header.split(' ')[1]
                except IndexError:
                    return jsonify({'message': 'Invalid authorization header format'}), 401
                    
            if not token:
                return jsonify({'message': 'Token is missing'}), 401
                
            try:
                payload = jwt_wrapper.verify_token(
                    token, 
                    algorithms=algorithms,
                    audience=audience,
                    issuer=issuer
                )
                request.jwt_payload = payload
            except ValueError as e:
                return jsonify({'message': str(e)}), 401
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/api/internal/data', methods=['GET'])
@token_required(algorithms=['HS256'])
def get_internal_data():
    return jsonify({
        'message': 'Internal data accessed',
        'user': request.jwt_payload.get('sub'),
        'data': {'internal': 'sensitive_data'}
    })

@app.route('/api/public/data', methods=['GET'])
@token_required(algorithms=['RS256'])
def get_public_data():
    return jsonify({
        'message': 'Public API data accessed',
        'user': request.jwt_payload.get('sub'),
        'data': {'public': 'api_data'}
    })

@app.route('/api/flexible/data', methods=['GET'])
@token_required(algorithms=['HS256', 'RS256'])
def get_flexible_data():
    return jsonify({
        'message': 'Flexible endpoint accessed',
        'user': request.jwt_payload.get('sub'),
        'algorithm': request.jwt_payload.get('alg', 'unknown'),
        'data': {'flexible': 'multi_algorithm_data'}
    })

@app.route('/api/verify', methods=['POST'])
def verify_token():
    data = request.get_json()
    token = data.get('token')
    algorithms = data.get('algorithms', ['HS256', 'RS256'])
    audience = data.get('audience')
    issuer = data.get('issuer')
    
    if not token:
        return jsonify({'error': 'Token is required'}), 400
        
    try:
        payload = jwt_wrapper.verify_token(
            token,
            algorithms=algorithms,
            audience=audience,
            issuer=issuer
        )
        return jsonify({
            'valid': True,
            'payload': payload
        })
    except ValueError as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 401

@app.route('/api/create', methods=['POST'])
def create_token():
    data = request.get_json()
    payload = data.get('payload', {})
    algorithm = data.get('algorithm', 'HS256')
    key_id = data.get('key_id')
    
    try:
        token = jwt_wrapper.create_token(payload, algorithm, key_id)
        return jsonify({'token': token})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/decode', methods=['POST'])
def decode_without_verification():
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token is required'}), 400
        
    try:
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
        return jsonify({
            'header': header,
            'payload': payload
        })
    except jwt.InvalidTokenError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=False, port=5000)