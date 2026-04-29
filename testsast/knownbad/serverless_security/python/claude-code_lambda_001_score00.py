import json
import boto3
import logging
from urllib.parse import unquote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:123456789012:image-processing-notifications'

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        logger.info(f"Processing {bucket}/{key}")
        
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            image_data = response['Body'].read()
            
            result_data = process_image(image_data)
            
            result_key = f"processed/{key}"
            s3_client.put_object(
                Bucket=bucket,
                Key=result_key,
                Body=json.dumps(result_data),
                ContentType='application/json'
            )
            
            message = f"Successfully processed image: {key}"
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject='Image Processing Complete',
                Message=message
            )
            
            logger.info(f"Successfully processed {key}")
            
        except Exception as e:
            logger.error(f"Error processing {key}: {str(e)}")
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject='Image Processing Failed',
                Message=f"Failed to process {key}: {str(e)}"
            )
            raise
    
    return {
        'statusCode': 200,
        'body': json.dumps('Image processing complete')
    }

def process_image(image_data):
    return {
        'size': len(image_data),
        'status': 'processed'
    }