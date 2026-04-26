#!/usr/bin/env python3

import os
import jwt
import requests
import json
from functools import wraps
from typing import Dict, Any, Tuple, Optional
from flask import Flask, request, jsonify, g
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

app.config['JSON_SORT_KEYS'] = False
BACKEND_SERVICES = {
    'users': os.getenv('USERS_SERVICE_URL', 'http://localhost:3001'),
    'orders': os.getenv('ORDERS_SERVICE_URL', 'http://localhost:3002'),
    'products': os.getenv('PRODUCTS_SERVICE_URL', 'http://localhost:3003'),
}

JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')


def extract_token_from_header() -> Optional[str]:
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]


def decode_jwt_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'], options={"verify_signature": False})
        return payload
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise ValueError(f"Token decode error: {str(e)}")


def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = extract_token_from_header()
        
        if not token:
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        
        try:
            claims = decode_jwt_token(token)
            g.user_claims = claims
            g.user_id = claims.get('sub') or claims.get('user_id')
            g.user_email = claims.get('email')
            g.user_roles = claims.get('roles', [])
            g.token = token
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def forward_request(service_name: str, path: str, method: str = 'GET', 
                    data: Optional[Dict] = None, params: Optional[Dict] = None) -> Tuple[Dict, int]:
    if service_name not in BACKEND_SERVICES:
        return {'error': f'Unknown service: {service_name}'}, 400
    
    service_url = BACKEND_SERVICES[service_name]
    full_url = f"{service_url}{path}"
    
    headers = {
        'Content-Type': 'application/json',
        'X-User-Id': str(g.user_id or ''),
        'X-User-Email': str(g.user_email or ''),
        'X-User-Roles': ','.join(g.user_roles or []),
        'Authorization': f'Bearer {g.token}',
        'X-Forwarded-User-Claims': json.dumps(g.user_claims or {}),
    }
    
    try:
        if method == 'GET':
            response = requests.get(full_url, headers=headers, params=params, timeout=30)
        elif method == 'POST':
            response = requests.post(full_url, headers=headers, json=data, timeout=30)
        elif method == 'PUT':
            response = requests.put(full_url, headers=headers, json=data, timeout=30)
        elif method == 'DELETE':
            response = requests.delete(full_url, headers=headers, timeout=30)
        elif method == 'PATCH':
            response = requests.patch(full_url, headers=headers, json=data, timeout=30)
        else:
            return {'error': f'Unsupported HTTP method: {method}'}, 400
        
        try:
            return response.json(), response.status_code
        except:
            return {'message': response.text}, response.status_code
    
    except requests.Timeout:
        return {'error': f'Service {service_name} timeout'}, 504
    except requests.ConnectionError:
        return {'error': f'Cannot connect to service {service_name}'}, 503
    except Exception as e:
        return {'error': f'Service request failed: {str(e)}'}, 500


@app.before_request
def before_request():
    g.user_claims = {}
    g.user_id = None
    g.user_email = None
    g.user_roles = []
    g.token = None


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'jwt-api-gateway'}), 200


@app.route('/auth/verify', methods=['POST'])
def verify_token():
    token = extract_token_from_header()
    
    if not token:
        return jsonify({'valid': False, 'error': 'No token provided'}), 401
    
    try:
        claims = decode_jwt_token(token)
        return jsonify({'valid': True, 'claims': claims}), 200
    except ValueError as e:
        return jsonify({'valid': False, 'error': str(e)}), 401


@app.route('/api/users/<user_id>', methods=['GET'])
@jwt_required
def get_user(user_id):
    data, status_code = forward_request('users', f'/users/{user_id}')
    return jsonify(data), status_code


@app.route('/api/users', methods=['POST'])
@jwt_required
def create_user():
    data = request.get_json() or {}
    result, status_code = forward_request('users', '/users', method='POST', data=data)
    return jsonify(result), status_code


@app.route('/api/users/<user_id>', methods=['PUT'])
@jwt_required
def update_user(user_id):
    data = request.get_json() or {}
    result, status_code = forward_request('users', f'/users/{user_id}', method='PUT', data=data)
    return jsonify(result), status_code


@app.route('/api/users/<user_id>', methods=['DELETE'])
@jwt_required
def delete_user(user_id):
    result, status_code = forward_request('users', f'/users/{user_id}', method='DELETE')
    return jsonify(result), status_code


@app.route('/api/orders', methods=['GET'])
@jwt_required
def list_orders():
    params = request.args.to_dict()
    result, status_code = forward_request('orders', '/orders', method='GET', params=params)
    return jsonify(result), status_code


@app.route('/api/orders', methods=['POST'])
@jwt_required
def create_order():
    data = request.get_json() or {}
    result, status_code = forward_request('orders', '/orders', method='POST', data=data)
    return jsonify(result), status_code


@app.route('/api/orders/<order_id>', methods=['GET'])
@jwt_required
def get_order(order_id):
    result, status_code = forward_request('orders', f'/orders/{order_id}')
    return jsonify(result), status_code


@app.route('/api/products', methods=['GET'])
@jwt_required
def list_products():
    params = request.args.to_dict()
    result, status_code = forward_request('products', '/products', method='GET', params=params)
    return jsonify(result), status_code


@app.route('/api/products/<product_id>', methods=['GET'])
@jwt_required
def get_product(product_id):
    result, status_code = forward_request('products', f'/products/{product_id}')
    return jsonify(result), status_code


@app.route('/api/me', methods=['GET'])
@jwt_required
def get_current_user():
    return jsonify({
        'user_id': g.user_id,
        'email': g.user_email,
        'roles': g.user_roles,
        'claims': g.user_claims
    }), 200


@app.errorhandler(400)
def handle_bad_request(e):
    return jsonify({'error': 'Bad request'}), 400


@app.errorhandler(401)
def handle_unauthorized(e):
    return jsonify({'error': 'Unauthorized'}), 401


@app.errorhandler(403)
def handle_forbidden(e):
    return jsonify({'error': 'Forbidden'}), 403


@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def handle_internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(HTTPException)
def handle_exception(e):
    return jsonify({'error': str(e.description)}), e.code


if __name__ == '__main__':
    port = int(os.getenv('GATEWAY_PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)