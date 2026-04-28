import json
import boto3
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns_client = boto3.client('sns')

class NotificationPublisher:
    def __init__(self):
        self.sns = sns_client
        
    def publish_notification(self, topic_arn: str, message: str, subject: str = None, 
                            notification_type: str = "default", 
                            attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            message_attributes = {
                'notification_type': {
                    'StringValue': notification_type,
                    'DataType': 'String'
                },
                'timestamp': {
                    'StringValue': datetime.utcnow().isoformat(),
                    'DataType': 'String'
                }
            }
            
            if attributes:
                for key, value in attributes.items():
                    if isinstance(value, str):
                        message_attributes[key] = {
                            'StringValue': value,
                            'DataType': 'String'
                        }
                    elif isinstance(value, (int, float)):
                        message_attributes[key] = {
                            'StringValue': str(value),
                            'DataType': 'Number'
                        }
            
            publish_params = {
                'TopicArn': topic_arn,
                'Message': message if isinstance(message, str) else json.dumps(message)
            }
            
            if subject:
                publish_params['Subject'] = subject
            
            if message_attributes:
                publish_params['MessageAttributes'] = message_attributes
            
            response = self.sns.publish(**publish_params)
            
            return {
                'statusCode': 200,
                'messageId': response['MessageId'],
                'notification_type': notification_type,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error publishing to SNS: {str(e)}")
            raise

def publish_alert_notification(topic_arn: str, alert_level: str, alert_message: str, 
                               details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    publisher = NotificationPublisher()
    
    message_body = {
        'alert_level': alert_level,
        'alert_message': alert_message,
        'details': details or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    attributes = {
        'alert_level': alert_level,
        'priority': '9' if alert_level == 'critical' else '5' if alert_level == 'warning' else '1'
    }
    
    return publisher.publish_notification(
        topic_arn=topic_arn,
        message=json.dumps(message_body),
        subject=f"Alert: {alert_level.upper()} - {alert_message}",
        notification_type="alert",
        attributes=attributes
    )

def publish_user_notification(topic_arn: str, user_id: str, notification_message: str, 
                             action_url: Optional[str] = None) -> Dict[str, Any]:
    publisher = NotificationPublisher()
    
    message_body = {
        'user_id': user_id,
        'message': notification_message,
        'action_url': action_url,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    attributes = {
        'user_id': user_id,
        'action_available': 'true' if action_url else 'false'
    }
    
    return publisher.publish_notification(
        topic_arn=topic_arn,
        message=json.dumps(message_body),
        subject=f"Notification for User {user_id}",
        notification_type="user_notification",
        attributes=attributes
    )

def publish_system_notification(topic_arn: str, system_event: str, status: str, 
                               metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    publisher = NotificationPublisher()
    
    message_body = {
        'system_event': system_event,
        'status': status,
        'metadata': metadata or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    attributes = {
        'event_type': system_event,
        'status': status
    }
    
    return publisher.publish_notification(
        topic_arn=topic_arn,
        message=json.dumps(message_body),
        subject=f"System Event: {system_event}",
        notification_type="system_event",
        attributes=attributes
    )

def lambda_handler(event, context):
    try:
        notification_type = event.get('notification_type', 'default')
        topic_arn = event.get('topic_arn')
        
        if not topic_arn:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing required parameter: topic_arn'),
                'error': 'MissingTopicArn'
            }
        
        result = None
        
        if notification_type == 'alert':
            alert_level = event.get('alert_level', 'info')
            alert_message = event.get('message', '')
            details = event.get('details', {})
            result = publish_alert_notification(topic_arn, alert_level, alert_message, details)
        
        elif notification_type == 'user_notification':
            user_id = event.get('user_id')
            message = event.get('message', '')
            action_url = event.get('action_url')
            
            if not user_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps('Missing required parameter: user_id'),
                    'error': 'MissingUserId'
                }
            
            result = publish_user_notification(topic_arn, user_id, message, action_url)
        
        elif notification_type == 'system_event':
            system_event = event.get('system_event', 'unknown')
            status = event.get('status', 'unknown')
            metadata = event.get('metadata', {})
            result = publish_system_notification(topic_arn, system_event, status, metadata)
        
        else:
            publisher = NotificationPublisher()
            message = event.get('message', '')
            subject = event.get('subject')
            attributes = event.get('attributes')
            result = publisher.publish_notification(
                topic_arn=topic_arn,
                message=message,
                subject=subject,
                notification_type=notification_type,
                attributes=attributes
            )
        
        logger.info(f"Successfully published {notification_type} notification: {result['messageId']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result),
            'messageId': result.get('messageId')
        }
    
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}'),
            'error': type(e).__name__
        }