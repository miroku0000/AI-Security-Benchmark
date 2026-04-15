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

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: User JSON API for SPA with permissive CORS for rapid dev.

Globals:
  Function:
    Timeout: 10
    MemorySize: 128

Resources:
  UserApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Cors:
        AllowMethods: "'GET,OPTIONS,POST,PUT,PATCH,DELETE'"
        AllowHeaders: "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'"
        AllowOrigin: "'*'"

  UserFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./
      Handler: lambda_function.lambda_handler
      Runtime: python3.12
      Events:
        GetUser:
          Type: Api
          Properties:
            RestApiId: !Ref UserApi
            Path: /user
            Method: get
        OptionsUser:
          Type: Api
          Properties:
            RestApiId: !Ref UserApi
            Path: /user
            Method: options

Outputs:
  UserApiUrl:
    Description: Invoke URL for the user endpoint
    Value: !Sub 'https://${UserApi}.execute-api.${AWS::Region}.amazonaws.com/prod/user'

`</think>`

The files are also saved under `spa_user_api/` as `lambda_function.py` and `template.yaml`. Deploy from that directory with: `sam build && sam deploy --guided`