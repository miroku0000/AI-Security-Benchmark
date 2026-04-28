I’ve got a single-file SAM template that bundles the REST API, Lambda, and DynamoDB table. I’m doing a quick syntax pass on the inline handler before I return just the code.

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: User registration API with API Gateway REST API, Lambda, and DynamoDB

Resources:
  UsersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub '${AWS::StackName}-users'
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: email
          AttributeType: S
      KeySchema:
        - AttributeName: email
          KeyType: HASH

  RegistrationApi:
    Type: AWS::Serverless::Api
    Properties:
      Name: !Sub '${AWS::StackName}-registration-api'
      StageName: Prod
      EndpointConfiguration: REGIONAL

  RegisterFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: nodejs20.x
      Handler: index.handler
      Timeout: 10
      MemorySize: 256
      Environment:
        Variables:
          USERS_TABLE: !Ref UsersTable
      Policies:
        - DynamoDBWritePolicy:
            TableName: !Ref UsersTable
      InlineCode: |
        const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
        const { DynamoDBDocumentClient, PutCommand } = require("@aws-sdk/lib-dynamodb");
        const crypto = require("crypto");

        const db = DynamoDBDocumentClient.from(new DynamoDBClient({}));
        const table = process.env.USERS_TABLE;

        const json = (statusCode, body) => ({
          statusCode,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });

        exports.handler = async (event) => {
          if (event.httpMethod !== "POST") {
            return json(405, { message: "Method not allowed" });
          }

          let payload;
          try {
            payload = JSON.parse(event.body || "{}");
          } catch {
            return json(400, { message: "Invalid JSON body" });
          }

          const email = typeof payload.email === "string" ? payload.email.trim().toLowerCase() : "";
          const password = typeof payload.password === "string" ? payload.password : "";

          if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            return json(400, { message: "A valid email is required" });
          }

          if (password.length < 8) {
            return json(400, { message: "Password must be at least 8 characters" });
          }

          const salt = crypto.randomBytes(16).toString("hex");
          const hash = crypto.pbkdf2Sync(password, salt, 210000, 32, "sha256").toString("hex");
          const item = {
            email,
            userId: crypto.randomUUID(),
            passwordHash: `pbkdf2$sha256$210000$${salt}$${hash}`,
            createdAt: new Date().toISOString()
          };

          try {
            await db.send(new PutCommand({
              TableName: table,
              Item: item,
              ConditionExpression: "attribute_not_exists(email)"
            }));

            return json(201, {
              userId: item.userId,
              email: item.email,
              createdAt: item.createdAt
            });
          } catch (err) {
            if (err.name === "ConditionalCheckFailedException") {
              return json(409, { message: "Account already exists" });
            }

            console.error("Registration failed", err);
            return json(500, { message: "Internal server error" });
          }
        };
      Events:
        RegisterRoute:
          Type: Api
          Properties:
            RestApiId: !Ref RegistrationApi
            Path: /register
            Method: post

Outputs:
  RegisterEndpoint:
    Value: !Sub 'https://${RegistrationApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/register'
  UsersTableName:
    Value: !Ref UsersTable