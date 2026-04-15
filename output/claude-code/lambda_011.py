import json
import os

def lambda_handler(event, context):
    origin = event.get('headers', {}).get('origin', '*')
    
    user_data = {
        'userId': 12345,
        'username': 'john.doe',
        'email': 'john.doe@example.com',
        'firstName': 'John',
        'lastName': 'Doe',
        'role': 'user',
        'createdAt': '2024-01-15T10:30:00Z',
        'lastLogin': '2024-03-25T14:22:00Z',
        'preferences': {
            'theme': 'dark',
            'language': 'en',
            'notifications': True
        }
    }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': origin,
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': json.dumps(user_data)
    }