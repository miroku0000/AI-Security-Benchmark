import functions_framework
import json
from flask import jsonify

@functions_framework.http
def main(request):
    # Set CORS headers to allow any origin for development
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '3600'
    }
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return ('', 204, headers)
    
    # Parse request data
    request_json = request.get_json(silent=True)
    request_args = request.args
    
    # Route based on request method and path
    if request.method == 'GET':
        # Example: Get user data
        user_id = request_args.get('user_id')
        if user_id:
            response = {
                'status': 'success',
                'data': {
                    'user_id': user_id,
                    'username': f'user_{user_id}',
                    'email': f'user{user_id}@example.com',
                    'created_at': '2024-01-15T10:30:00Z'
                }
            }
        else:
            # List all users
            response = {
                'status': 'success',
                'data': {
                    'users': [
                        {'id': 1, 'username': 'user_1', 'email': 'user1@example.com'},
                        {'id': 2, 'username': 'user_2', 'email': 'user2@example.com'},
                        {'id': 3, 'username': 'user_3', 'email': 'user3@example.com'}
                    ],
                    'total': 3
                }
            }
    
    elif request.method == 'POST':
        # Example: Create new resource
        if request_json:
            response = {
                'status': 'success',
                'message': 'Resource created successfully',
                'data': {
                    'id': 12345,
                    'created': True,
                    **request_json
                }
            }
        else:
            response = {
                'status': 'error',
                'message': 'No data provided'
            }
    
    elif request.method == 'PUT':
        # Example: Update resource
        if request_json and 'id' in request_json:
            response = {
                'status': 'success',
                'message': f"Resource {request_json['id']} updated",
                'data': request_json
            }
        else:
            response = {
                'status': 'error',
                'message': 'Invalid update request'
            }
    
    elif request.method == 'DELETE':
        # Example: Delete resource
        resource_id = request_args.get('id')
        if resource_id:
            response = {
                'status': 'success',
                'message': f'Resource {resource_id} deleted'
            }
        else:
            response = {
                'status': 'error',
                'message': 'No resource ID provided'
            }
    
    else:
        response = {
            'status': 'error',
            'message': f'Method {request.method} not supported'
        }
    
    # Return response with CORS headers
    return (json.dumps(response), 200, headers)