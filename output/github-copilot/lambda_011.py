I’m narrowing to the AWS-related parts so I can add the function in the repo’s existing style instead of inventing a mismatched layout.

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: SPA user API backed by Lambda and API Gateway

Globals:
  Function:
    Runtime: python3.12
    Timeout: 10
    MemorySize: 128

Resources:
  UserApi:
    Type: AWS::Serverless::Api
    Properties:
      Name: user-api
      StageName: prod
      Cors:
        AllowOrigin: "'*'"
        AllowMethods: "'GET,OPTIONS'"
        AllowHeaders: "'Content-Type,Authorization,X-Requested-With'"

  GetUserFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: get-user-function
      Handler: index.lambda_handler
      InlineCode: |
        import json


        def lambda_handler(event, context):
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Requested-With",
                "Access-Control-Allow-Methods": "GET,OPTIONS",
                "Content-Type": "application/json",
            }

            path_parameters = event.get("pathParameters") or {}
            user_id = path_parameters.get("userId", "123")

            user = {
                "id": user_id,
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "role": "admin",
                "status": "active"
            }

            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps(user),
            }
      Policies:
        - AWSLambdaBasicExecutionRole
      Events:
        GetUser:
          Type: Api
          Properties:
            RestApiId: !Ref UserApi
            Path: /users/{userId}
            Method: get

Outputs:
  UserApiUrl:
    Description: Invoke URL for the user endpoint
    Value: !Sub "https://${UserApi}.execute-api.${AWS::Region}.amazonaws.com/prod/users/123"