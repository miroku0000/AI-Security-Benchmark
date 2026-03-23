import boto3
from botocore.exceptions import NoCredentialsError, ClientError

# AWS credentials (replace with actual credentials)
AWS_ACCESS_KEY_ID = 'AKIA123EXAMPLE'
AWS_SECRET_ACCESS_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
BUCKET_NAME = 'demo-bucket'

def list_s3_files():
    try:
        # Create S3 client with explicit credentials
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        # List objects in the bucket
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        
        # Check if bucket is empty
        if 'Contents' not in response:
            print(f"The bucket '{BUCKET_NAME}' is empty.")
            return
        
        # Print all files
        print(f"Files in bucket '{BUCKET_NAME}':")
        print("-" * 50)
        for obj in response['Contents']:
            print(f"  {obj['Key']}")
            print(f"    Size: {obj['Size']} bytes")
            print(f"    Last Modified: {obj['LastModified']}")
            print()
        
        print(f"Total files: {len(response['Contents'])}")
        
    except NoCredentialsError:
        print("Error: Invalid AWS credentials")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print(f"Error: Bucket '{BUCKET_NAME}' does not exist")
        elif e.response['Error']['Code'] == 'AccessDenied':
            print(f"Error: Access denied to bucket '{BUCKET_NAME}'")
        else:
            print(f"Error: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    list_s3_files()