# Public S3 Upload API (SAM)

Deploy:

sam build
sam deploy --guided

Invoke:

curl -X POST \
  -H 'Content-Type: application/octet-stream' \
  --data-binary @./somefile.bin \
  "$(aws cloudformation describe-stacks --stack-name <stack-name> --query "Stacks[0].Outputs[?OutputKey=='UploadEndpoint'].OutputValue" --output text)"

