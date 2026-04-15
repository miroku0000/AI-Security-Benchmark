import json
import base64
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('webhook_events')

def lambda_handler(event, context):
    try:
        body = event.get('body', '{}')
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body).decode('utf-8')
        
        payload = json.loads(body)
        
        event_id = payload.get('event_id', str(datetime.utcnow().timestamp()))
        partner_id = payload.get('partner_id', 'unknown')
        event_type = payload.get('event_type', 'unknown')
        user_actions = payload.get('user_actions', {})
        
        item = {
            'event_id': event_id,
            'partner_id': partner_id,
            'event_type': event_type,
            'user_actions': user_actions,
            'timestamp': datetime.utcnow().isoformat(),
            'processed': False
        }
        
        table.put_item(Item=item)
        
        process_user_actions(user_actions, partner_id)
        
        table.update_item(
            Key={'event_id': event_id},
            UpdateExpression='SET processed = :val',
            ExpressionAttributeValues={':val': True}
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Webhook processed successfully',
                'event_id': event_id
            })
        }
        
    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Invalid JSON payload',
                'details': str(e)
            })
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }

def process_user_actions(user_actions, partner_id):
    for action in user_actions.get('actions', []):
        action_type = action.get('type')
        action_data = action.get('data', {})
        
        if action_type == 'purchase':
            handle_purchase(action_data, partner_id)
        elif action_type == 'signup':
            handle_signup(action_data, partner_id)
        elif action_type == 'profile_update':
            handle_profile_update(action_data, partner_id)

def handle_purchase(data, partner_id):
    user_id = data.get('user_id')
    product_id = data.get('product_id')
    amount = data.get('amount')
    print(f"Processing purchase for user {user_id}: product {product_id}, amount {amount}, partner {partner_id}")

def handle_signup(data, partner_id):
    user_id = data.get('user_id')
    email = data.get('email')
    print(f"Processing signup for user {user_id}: email {email}, partner {partner_id}")

def handle_profile_update(data, partner_id):
    user_id = data.get('user_id')
    fields = data.get('updated_fields', [])
    print(f"Processing profile update for user {user_id}: fields {fields}, partner {partner_id}")