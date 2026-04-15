import jwt
import json
import time
from typing import Dict, Any, Optional, List, Union
from functools import wraps
from flask import request, jsonify, current_app
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

class JWTManager:
    def __init__(self, app=None):
        self.app = app
        self.algorithms = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512']
        self.secret_keys = {}
        self.public_keys = {}
        self.issuer_configs = {}
        self.default_algorithm = 'HS256'
        self.token_location = ['headers', 'cookies', 'query_string']
        self.header_name = 'Authorization'
        self.header_prefix = 'Bearer'
        self.cookie_name = 'jwt_token'
        self.query_param_name = 'token'
        self.leeway = 10
        self.verify_exp = True
        self.verify_iat = True
        self.verify_nbf = True
        self.require_exp = False
        self.require_iat = False
        self.require_nbf = False
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        app.jwt_manager = self
        
        self.secret_keys = app.config.get('JWT_SECRET_KEYS', {})
        self.public_keys = app.config.get('JWT_PUBLIC_KEYS', {})
        self.issuer_configs = app.config.get('JWT_ISSUER_CONFIGS', {})
        self.default_algorithm = app.config.get('JWT_DEFAULT_ALGORITHM', 'HS256')
        self.token_location = app.config.get('JWT_TOKEN_LOCATION', ['headers'])
        self.header_name = app.config.get('JWT_HEADER_NAME', 'Authorization')
        self.header_prefix = app.config.get('JWT_HEADER_PREFIX', 'Bearer')
        self.cookie_name = app.config.get('JWT_COOKIE_NAME', 'jwt_token')
        self.query_param_name = app.config.get('JWT_QUERY_PARAM_NAME', 'token')
        self.leeway = app.config.get('JWT_LEEWAY', 10)
        self.verify_exp = app.config.get('JWT_VERIFY_EXP', True)
        self.verify_iat = app.config.get('JWT_VERIFY_IAT', True)
        self.verify_nbf = app.config.get('JWT_VERIFY_NBF', True)
        self.require_exp = app.config.get('JWT_REQUIRE_EXP', False)
        self.require_iat = app.config.get('JWT_REQUIRE_IAT', False)
        self.require_nbf = app.config.get('JWT_REQUIRE_NBF', False)
    
    def add_secret_key(self, key_id: str, secret: str, algorithm: str = 'HS256'):
        self.secret_keys[key_id] = {
            'secret': secret,
            'algorithm': algorithm
        }
    
    def add_public_key(self, key_id: str, public_key: str, algorithm: str = 'RS256'):
        self.public_keys[key_id] = {
            'key': public_key,
            'algorithm': algorithm
        }
    
    def add_issuer_config(self, issuer: str, config: Dict[str, Any]):
        self.issuer_configs[issuer] = config
    
    def get_token_from_request(self) -> Optional[str]:
        token = None
        
        if 'headers' in self.token_location:
            auth_header = request.headers.get(self.header_name)
            if auth_header:
                parts = auth_header.split()
                if len(parts) == 2 and parts[0] == self.header_prefix:
                    token = parts[1]
        
        if not token and 'cookies' in self.token_location:
            token = request.cookies.get(self.cookie_name)
        
        if not token and 'query_string' in self.token_location:
            token = request.args.get(self.query_param_name)
        
        return token
    
    def decode_token(self, token: str, verify: bool = True) -> Dict[str, Any]:
        if not verify:
            return jwt.decode(token, options={"verify_signature": False})
        
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        header = jwt.get_unverified_header(token)
        algorithm = header.get('alg')
        kid = header.get('kid')
        issuer = unverified_payload.get('iss')
        
        verification_key = None
        algorithms = [algorithm] if algorithm else self.algorithms
        
        if issuer and issuer in self.issuer_configs:
            config = self.issuer_configs[issuer]
            if 'secret' in config:
                verification_key = config['secret']
            elif 'public_key' in config:
                verification_key = config['public_key']
            if 'algorithm' in config:
                algorithms = [config['algorithm']]
        elif kid:
            if kid in self.secret_keys:
                verification_key = self.secret_keys[kid]['secret']
                algorithms = [self.secret_keys[kid]['algorithm']]
            elif kid in self.public_keys:
                verification_key = self.public_keys[kid]['key']
                algorithms = [self.public_keys[kid]['algorithm']]
        else:
            for key_id, key_config in self.secret_keys.items():
                try:
                    return jwt.decode(
                        token,
                        key_config['secret'],
                        algorithms=[key_config['algorithm']],
                        leeway=self.leeway,
                        options={
                            'verify_exp': self.verify_exp,
                            'verify_iat': self.verify_iat,
                            'verify_nbf': self.verify_nbf,
                            'require_exp': self.require_exp,
                            'require_iat': self.require_iat,
                            'require_nbf': self.require_nbf
                        }
                    )
                except:
                    continue
            
            for key_id, key_config in self.public_keys.items():
                try:
                    return jwt.decode(
                        token,
                        key_config['key'],
                        algorithms=[key_config['algorithm']],
                        leeway=self.leeway,
                        options={
                            'verify_exp': self.verify_exp,
                            'verify_iat': self.verify_iat,
                            'verify_nbf': self.verify_nbf,
                            'require_exp': self.require_exp,
                            'require_iat': self.require_iat,
                            'require_nbf': self.require_nbf
                        }
                    )
                except:
                    continue
        
        if verification_key:
            return jwt.decode(
                token,
                verification_key,
                algorithms=algorithms,
                leeway=self.leeway,
                options={
                    'verify_exp': self.verify_exp,
                    'verify_iat': self.verify_iat,
                    'verify_nbf': self.verify_nbf,
                    'require_exp': self.require_exp,
                    'require_iat': self.require_iat,
                    'require_nbf': self.require_nbf
                }
            )
        
        raise jwt.InvalidTokenError('No valid key found for token verification')
    
    def encode_token(self, payload: Dict[str, Any], key_id: Optional[str] = None, 
                    algorithm: Optional[str] = None, issuer: Optional[str] = None) -> str:
        if issuer and issuer in self.issuer_configs:
            config = self.issuer_configs[issuer]
            secret = config.get('secret')
            algorithm = algorithm or config.get('algorithm', self.default_algorithm)
            headers = config.get('headers', {})
        elif key_id and key_id in self.secret_keys:
            secret = self.secret_keys[key_id]['secret']
            algorithm = algorithm or self.secret_keys[key_id]['algorithm']
            headers = {'kid': key_id}
        else:
            if not self.secret_keys:
                raise ValueError('No secret keys configured')
            first_key_id = list(self.secret_keys.keys())[0]
            secret = self.secret_keys[first_key_id]['secret']
            algorithm = algorithm or self.secret_keys[first_key_id]['algorithm']
            headers = {'kid': first_key_id}
        
        if not algorithm:
            algorithm = self.default_algorithm
        
        if 'iat' not in payload:
            payload['iat'] = int(time.time())
        
        return jwt.encode(payload, secret, algorithm=algorithm, headers=headers)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = self.decode_token(token, verify=True)
            return {'valid': True, 'payload': payload}
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'error': 'Token has expired'}
        except jwt.InvalidTokenError as e:
            return {'valid': False, 'error': str(e)}
        except Exception as e:
            return {'valid': False, 'error': f'Token validation failed: {str(e)}'}
    
    def extract_payload(self, token: str, verify: bool = True) -> Optional[Dict[str, Any]]:
        try:
            return self.decode_token(token, verify=verify)
        except:
            return None
    
    def get_claims(self, token: str, claims: List[str], verify: bool = True) -> Dict[str, Any]:
        payload = self.extract_payload(token, verify=verify)
        if not payload:
            return {}
        return {claim: payload.get(claim) for claim in claims}
    
    def jwt_required(self, optional: bool = False, fresh: bool = False, 
                    verify_type: bool = True, skip_revocation_check: bool = False):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                token = self.get_token_from_request()
                
                if not token:
                    if optional:
                        request.jwt_payload = None
                        return fn(*args, **kwargs)
                    return jsonify({'error': 'Missing JWT token'}), 401
                
                result = self.verify_token(token)
                
                if not result['valid']:
                    if optional:
                        request.jwt_payload = None
                        return fn(*args, **kwargs)
                    return jsonify({'error': result['error']}), 401
                
                payload = result['payload']
                
                if fresh and not payload.get('fresh', False):
                    return jsonify({'error': 'Fresh token required'}), 401
                
                if verify_type:
                    token_type = payload.get('type', 'access')
                    if token_type != 'access':
                        return jsonify({'error': 'Only access tokens are allowed'}), 422
                
                if not skip_revocation_check and hasattr(self, 'is_token_revoked'):
                    if self.is_token_revoked(payload):
                        return jsonify({'error': 'Token has been revoked'}), 401
                
                request.jwt_payload = payload
                request.jwt_token = token
                return fn(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def jwt_refresh_token_required(self, optional: bool = False):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                token = self.get_token_from_request()
                
                if not token:
                    if optional:
                        request.jwt_payload = None
                        return fn(*args, **kwargs)
                    return jsonify({'error': 'Missing JWT refresh token'}), 401
                
                result = self.verify_token(token)
                
                if not result['valid']:
                    if optional:
                        request.jwt_payload = None
                        return fn(*args, **kwargs)
                    return jsonify({'error': result['error']}), 401
                
                payload = result['payload']
                token_type = payload.get('type', 'access')
                
                if token_type != 'refresh':
                    return jsonify({'error': 'Only refresh tokens are allowed'}), 422
                
                request.jwt_payload = payload
                request.jwt_token = token
                return fn(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def create_access_token(self, identity: Any, fresh: bool = False, 
                           expires_delta: Optional[int] = None, 
                           additional_claims: Optional[Dict[str, Any]] = None) -> str:
        payload = {
            'identity': identity,
            'type': 'access',
            'fresh': fresh
        }
        
        if expires_delta:
            payload['exp'] = int(time.time()) + expires_delta
        
        if additional_claims:
            payload.update(additional_claims)
        
        return self.encode_token(payload)
    
    def create_refresh_token(self, identity: Any, expires_delta: Optional[int] = None,
                           additional_claims: Optional[Dict[str, Any]] = None) -> str:
        payload = {
            'identity': identity,
            'type': 'refresh'
        }
        
        if expires_delta:
            payload['exp'] = int(time.time()) + expires_delta
        
        if additional_claims:
            payload.update(additional_claims)
        
        return self.encode_token(payload)
    
    def get_jwt_identity(self) -> Any:
        return request.jwt_payload.get('identity') if hasattr(request, 'jwt_payload') else None
    
    def get_jwt(self) -> Optional[Dict[str, Any]]:
        return request.jwt_payload if hasattr(request, 'jwt_payload') else None
    
    def get_current_user(self) -> Any:
        return self.get_jwt_identity()
    
    def decode_complete_token(self, token: str) -> Dict[str, Any]:
        header = jwt.get_unverified_header(token)
        payload = self.extract_payload(token, verify=False)
        return {
            'header': header,
            'payload': payload
        }