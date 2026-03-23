#!/usr/bin/env python3
import boto3
from botocore.config import Config

AWS_ACCESS_KEY_ID = "AKIA123EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
BUCKET_NAME = "demo-bucket"
REGION = "us-east-1"


def main() -> None:
    client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=REGION,
        config=Config(signature_version="s3v4"),
    )

    paginator = client.get_paginator("list_objects_v2")
    count = 0
    for page in paginator.paginate(Bucket=BUCKET_NAME):
        for obj in page.get("Contents", []):
            print(obj["Key"])
            count += 1

    if count == 0:
        print("(bucket is empty or no objects listed)")


if __name__ == "__main__":
    main()
