# Shared IAM role definition example for all similar Lambda functions.
# Scope the resource ARNs to only the buckets, tables, topics, and queues your services actually use.
#
# {
#   "RoleName": "shared-microservice-lambda-role",
#   "AssumeRolePolicyDocument": {
#     "Version": "2012-10-17",
#     "Statement": [
#       {
#         "Effect": "Allow",
#         "Principal": { "Service": "lambda.amazonaws.com" },
#         "Action": "sts:AssumeRole"
#       }
#     ]
#   },
#   "Policies": [
#     {
#       "PolicyName": "shared-microservice-access",
#       "PolicyDocument": {
#         "Version": "2012-10-17",
#         "Statement": [
#           {
#             "Sid": "CloudWatchLogs",
#             "Effect": "Allow",
#             "Action": [
#               "logs:CreateLogGroup",
#               "logs:CreateLogStream",
#               "logs:PutLogEvents"
#             ],
#             "Resource": "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:*"
#           },
#           {
#             "Sid": "S3LeastPrivilege",
#             "Effect": "Allow",
#             "Action": [
#               "s3:GetObject",
#               "s3:PutObject",
#               "s3:AbortMultipartUpload"
#             ],
#             "Resource": [
#               "arn:aws:s3:::${APP_BUCKET_ONE}/*",
#               "arn:aws:s3:::${APP_BUCKET_TWO}/*"
#             ],
#             "Condition": {
#               "Bool": { "aws:SecureTransport": "true" }
#             }
#           },
#           {
#             "Sid": "DynamoDBLeastPrivilege",
#             "Effect": "Allow",
#             "Action": [
#               "dynamodb:GetItem",
#               "dynamodb:PutItem",
#               "dynamodb:UpdateItem",
#               "dynamodb:Query"
#             ],
#             "Resource": [
#               "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/${APP_TABLE_ONE}",
#               "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/${APP_TABLE_TWO}"
#             ]
#           },
#           {
#             "Sid": "SNSLeastPrivilege",
#             "Effect": "Allow",
#             "Action": [ "sns:Publish" ],
#             "Resource": [
#               "arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:${APP_TOPIC_ONE}",
#               "arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:${APP_TOPIC_TWO}"
#             ]
#           },
#           {
#             "Sid": "SQSLeastPrivilege",
#             "Effect": "Allow",
#             "Action": [
#               "sqs:GetQueueAttributes",
#               "sqs:SendMessage"
#             ],
#             "Resource": [
#               "arn:aws:sqs:${AWS_REGION}:${AWS_ACCOUNT_ID}:${APP_QUEUE_ONE}",
#               "arn:aws:sqs:${AWS_REGION}:${AWS_ACCOUNT_ID}:${APP_QUEUE_TWO}"
#             ]
#           }
#         ]
#       }
#     }
#   ]
# }