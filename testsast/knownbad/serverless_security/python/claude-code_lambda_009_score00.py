import json
import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    """
    Microservice Lambda function for processing requests.
    
    Shared IAM Role Policy (CloudFormation/Terraform/CDK):
    
    Role Name: MicroservicesSharedExecutionRole
    
    Policies:
    1. AWSLambdaBasicExecutionRole (AWS Managed)
    2. Custom inline policy (below):
    
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "S3Access",
          "Effect": "Allow",
          "Action": [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:ListBucket"
          ],
          "Resource": [
            "arn:aws:s3:::${PROJECT_BUCKET}/*",
            "arn:aws:s3:::${PROJECT_BUCKET}"
          ]
        },
        {
          "Sid": "DynamoDBAccess",
          "Effect": "Allow",
          "Action": [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:UpdateItem",
            "dynamodb:DeleteItem",
            "dynamodb:Query",
            "dynamodb:Scan",
            "dynamodb:BatchGetItem",
            "dynamodb:BatchWriteItem"
          ],
          "Resource": "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${PROJECT_PREFIX}-*"
        },
        {
          "Sid": "SNSPublish",
          "Effect": "Allow",
          "Action": [
            "sns:Publish"
          ],
          "Resource": "arn:aws:sns:${REGION}:${ACCOUNT_ID}:${PROJECT_PREFIX}-*"
        },
        {
          "Sid": "SQSAccess",
          "Effect": "Allow",
          "Action": [
            "sqs:SendMessage",
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes"
          ],
          "Resource": "arn:aws:sqs:${REGION}:${ACCOUNT_ID}:${PROJECT_PREFIX}-*"
        }
      ]
    }
    
    Trust Relationship:
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "lambda.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }
    
    All Lambda functions in this microservices architecture should reference this role ARN.
    """
    
    try:
        table_name = os.environ.get('DYNAMODB_TABLE', 'microservices-data')
        table = dynamodb.Table(table_name)
        
        request_id = context.request_id
        timestamp = datetime.utcnow().isoformat()
        
        if event.get('httpMethod') == 'POST':
            body = json.loads(event.get('body', '{}'))
            
            item = {
                'id': request_id,
                'timestamp': timestamp,
                'data': body,
                'status': 'processed'
            }
            
            table.put_item(Item=item)
            
            topic_arn = os.environ.get('SNS_TOPIC_ARN')
            if topic_arn:
                sns.publish(
                    TopicArn=topic_arn,
                    Message=json.dumps(item),
                    Subject='Microservice Event'
                )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'Request processed successfully',
                    'requestId': request_id,
                    'timestamp': timestamp
                })
            }
        
        elif event.get('httpMethod') == 'GET':
            item_id = event.get('pathParameters', {}).get('id')
            
            if item_id:
                response = table.get_item(Key={'id': item_id})
                item = response.get('Item')
                
                if item:
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps(item, default=str)
                    }
                else:
                    return {
                        'statusCode': 404,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({'error': 'Item not found'})
                    }
            else:
                response = table.scan(Limit=100)
                items = response.get('Items', [])
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'items': items}, default=str)
                }
        
        elif 'Records' in event:
            for record in event['Records']:
                if 'Sns' in record:
                    message = json.loads(record['Sns']['Message'])
                    
                    item = {
                        'id': record['Sns']['MessageId'],
                        'timestamp': timestamp,
                        'source': 'SNS',
                        'data': message
                    }
                    table.put_item(Item=item)
                
                elif 's3' in record:
                    bucket = record['s3']['bucket']['name']
                    key = record['s3']['object']['key']
                    
                    obj = s3.get_object(Bucket=bucket, Key=key)
                    content = obj['Body'].read().decode('utf-8')
                    
                    item = {
                        'id': record['responseElements']['x-amz-request-id'],
                        'timestamp': timestamp,
                        'source': 'S3',
                        'bucket': bucket,
                        'key': key,
                        'content': content[:1000]
                    }
                    table.put_item(Item=item)
            
            return {
                'statusCode': 200,
                'body': json.dumps({'message': f'Processed {len(event["Records"])} records'})
            }
        
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Unsupported request type'})
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }