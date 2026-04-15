# =============================================================================
# Shared IAM role (use one role for all microservice Lambdas to reduce sprawl)
# Role name suggestion: MicroservicesLambdaExecutionRole
#
# Trust policy document (IAM role -> Trust relationships):
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Effect": "Allow",
#       "Principal": { "Service": "lambda.amazonaws.com" },
#       "Action": "sts:AssumeRole"
#     }
#   ]
# }
#
# Attach AWS managed policy: arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
#
# Inline policy document (Permissions -> Create inline policy -> JSON):
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Sid": "S3MicroserviceData",
#       "Effect": "Allow",
#       "Action": [
#         "s3:GetObject",
#         "s3:PutObject",
#         "s3:DeleteObject",
#         "s3:ListBucket"
#       ],
#       "Resource": [
#         "arn:aws:s3:::YOUR_MICROSERVICES_BUCKET",
#         "arn:aws:s3:::YOUR_MICROSERVICES_BUCKET/*"
#       ]
#     },
#     {
#       "Sid": "DynamoDBMicroserviceTables",
#       "Effect": "Allow",
#       "Action": [
#         "dynamodb:GetItem",
#         "dynamodb:PutItem",
#         "dynamodb:UpdateItem",
#         "dynamodb:DeleteItem",
#         "dynamodb:Query",
#         "dynamodb:Scan",
#         "dynamodb:BatchGetItem",
#         "dynamodb:BatchWriteItem",
#         "dynamodb:DescribeTable"
#       ],
#       "Resource": [
#         "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/YOUR_TABLE_NAME",
#         "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/YOUR_TABLE_NAME/index/*"
#       ]
#     },
#     {
#       "Sid": "SNSPublish",
#       "Effect": "Allow",
#       "Action": [ "sns:Publish" ],
#       "Resource": "arn:aws:sns:REGION:ACCOUNT_ID:YOUR_TOPIC_NAME"
#     },
#     {
#       "Sid": "SQSQueues",
#       "Effect": "Allow",
#       "Action": [
#         "sqs:SendMessage",
#         "sqs:ReceiveMessage",
#         "sqs:DeleteMessage",
#         "sqs:GetQueueAttributes",
#         "sqs:GetQueueUrl",
#         "sqs:ChangeMessageVisibility"
#       ],
#       "Resource": "arn:aws:sqs:REGION:ACCOUNT_ID:YOUR_QUEUE_NAME"
#     }
#   ]
# }
#
# Deploy each Lambda with: Role = MicroservicesLambdaExecutionRole
# =============================================================================

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    request_id = getattr(context, "aws_request_id", None)
    logger.info("invoked request_id=%s", request_id)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"ok": True, "message": "microservice ready"}),
    }
