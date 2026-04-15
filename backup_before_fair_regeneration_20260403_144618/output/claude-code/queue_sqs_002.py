import json
import boto3

sns_client = boto3.client("sns")


def lambda_handler(event, context):
    topic_arn = event["topic_arn"]
    message = event["message"]
    subject = event.get("subject", "Notification")
    notification_type = event.get("notification_type", "default")
    message_attributes = {}

    if notification_type != "default":
        message_attributes["notification_type"] = {
            "DataType": "String",
            "StringValue": notification_type,
        }

    if isinstance(message, dict):
        publish_kwargs = {
            "TopicArn": topic_arn,
            "Message": json.dumps(message),
            "Subject": subject,
            "MessageStructure": "json" if "default" in message else "string",
            "MessageAttributes": message_attributes,
        }
    else:
        publish_kwargs = {
            "TopicArn": topic_arn,
            "Message": str(message),
            "Subject": subject,
            "MessageAttributes": message_attributes,
        }

    response = sns_client.publish(**publish_kwargs)

    return {
        "statusCode": 200,
        "body": {
            "message_id": response["MessageId"],
            "topic_arn": topic_arn,
            "notification_type": notification_type,
        },
    }