import json

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": (
        "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token"
    ),
    "Access-Control-Allow-Methods": "GET,OPTIONS,POST,PUT,PATCH,DELETE",
}


def lambda_handler(event, context):
    method = event.get("httpMethod")
    if not method and event.get("requestContext", {}).get("http"):
        method = event["requestContext"]["http"].get("method")
    method = (method or "GET").upper()

    if method == "OPTIONS":
        return {"statusCode": 204, "headers": CORS_HEADERS, "body": ""}

    user_data = {
        "id": "usr_01HZZZZZZZZZZZZZZZZZZZZZZ",
        "email": "developer@example.com",
        "name": "Demo User",
        "role": "developer",
        "preferences": {"theme": "dark", "notifications": True},
    }

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps(user_data),
    }
