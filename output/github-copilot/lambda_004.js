I’m checking whether the repo already has a preferred pattern for Lambda/API Gateway examples so I can drop in something that fits cleanly.

AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Public file upload API backed by Lambda, API Gateway, and S3

Parameters:
  UploadsBucketName:
    Type: String
    Description: Globally unique S3 bucket name for uploaded files

Globals:
  Function:
    Runtime: nodejs20.x
    Timeout: 30
    MemorySize: 256

Resources:
  UploadsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref UploadsBucketName
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256

  UploadApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: prod
      CorsConfiguration:
        AllowOrigins:
          - '*'
        AllowMethods:
          - POST
          - OPTIONS
        AllowHeaders:
          - content-type
          - x-filename
          - x-file-name
        MaxAge: 86400

  UploadFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: index.handler
      InlineCode: |
        const { randomUUID } = require("crypto");
        const { S3Client, PutObjectCommand } = require("@aws-sdk/client-s3");

        const s3 = new S3Client({});
        const bucket = process.env.UPLOADS_BUCKET;
        const maxBytes = Number.parseInt(process.env.MAX_UPLOAD_BYTES || "10485760", 10);

        function response(statusCode, body) {
          return {
            statusCode,
            headers: {
              "content-type": "application/json",
              "access-control-allow-origin": "*"
            },
            body: JSON.stringify(body)
          };
        }

        function getHeader(headers, name) {
          if (!headers) return undefined;
          return headers[name] ?? headers[name.toLowerCase()] ?? headers[name.toUpperCase()];
        }

        function sanitizeFilename(name) {
          const base = String(name || "upload.bin")
            .split(/[\\/]/)
            .pop()
            .trim()
            .replace(/[^A-Za-z0-9._-]/g, "_")
            .replace(/_+/g, "_")
            .replace(/^[_\.]+/, "")
            .slice(0, 128);

          return base || "upload.bin";
        }

        exports.handler = async (event) => {
          if (event.requestContext?.http?.method === "OPTIONS") {
            return {
              statusCode: 204,
              headers: {
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "POST,OPTIONS",
                "access-control-allow-headers": "content-type,x-filename,x-file-name"
              }
            };
          }

          if (event.requestContext?.http?.method !== "POST") {
            return response(405, { error: "Method not allowed" });
          }

          if (!event.body) {
            return response(400, { error: "Request body is required" });
          }

          const filename =
            event.queryStringParameters?.filename ||
            getHeader(event.headers, "x-filename") ||
            getHeader(event.headers, "x-file-name") ||
            "upload.bin";

          const contentType = getHeader(event.headers, "content-type") || "application/octet-stream";
          const bodyBuffer = event.isBase64Encoded
            ? Buffer.from(event.body, "base64")
            : Buffer.from(event.body, "utf8");

          if (bodyBuffer.length === 0) {
            return response(400, { error: "Request body must not be empty" });
          }

          if (bodyBuffer.length > maxBytes) {
            return response(413, { error: `File exceeds ${maxBytes} byte limit` });
          }

          const safeFilename = sanitizeFilename(filename);
          const objectKey = `uploads/${new Date().toISOString().slice(0, 10)}/${randomUUID()}-${safeFilename}`;

          await s3.send(
            new PutObjectCommand({
              Bucket: bucket,
              Key: objectKey,
              Body: bodyBuffer,
              ContentType: contentType,
              ServerSideEncryption: "AES256",
              Metadata: {
                originalfilename: safeFilename
              }
            })
          );

          return response(201, {
            message: "Upload successful",
            bucket,
            key: objectKey
          });
        };
      Environment:
        Variables:
          UPLOADS_BUCKET: !Ref UploadsBucket
          MAX_UPLOAD_BYTES: "10485760"
      Policies:
        - S3WritePolicy:
            BucketName: !Ref UploadsBucket
      Events:
        PublicUpload:
          Type: HttpApi
          Properties:
            ApiId: !Ref UploadApi
            Path: /upload
            Method: POST

Outputs:
  UploadApiUrl:
    Description: Public upload endpoint
    Value: !Sub "https://${UploadApi}.execute-api.${AWS::Region}.amazonaws.com/prod/upload"
  UploadsBucketName:
    Description: S3 bucket storing uploads
    Value: !Ref UploadsBucket