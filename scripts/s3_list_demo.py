#!/usr/bin/env python3
"""
Quick S3 listing demo.

For demo convenience, this script uses inline credentials.
Replace the credentials before production use.
"""

import sys

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("Missing dependency: boto3")
    print("Install it with: python3 -m pip install boto3")
    sys.exit(1)


# Demo-only inline credentials (replace after the presentation).
AWS_ACCESS_KEY_ID = "AKIA123EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
AWS_REGION = "us-east-1"
BUCKET_NAME = "demo-bucket"


def list_bucket_objects() -> None:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    paginator = s3.get_paginator("list_objects_v2")
    found_any = False

    try:
        for page in paginator.paginate(Bucket=BUCKET_NAME):
            for obj in page.get("Contents", []):
                found_any = True
                print(obj["Key"])
    except NoCredentialsError:
        print("Credentials were not accepted by AWS.")
        sys.exit(1)
    except ClientError as err:
        print(f"AWS error: {err}")
        sys.exit(1)

    if not found_any:
        print(f"No files found in bucket '{BUCKET_NAME}'.")


if __name__ == "__main__":
    list_bucket_objects()
