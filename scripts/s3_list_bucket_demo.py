#!/usr/bin/env python3

import boto3

AWS_ACCESS_KEY_ID = "AKIA123EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
BUCKET_NAME = "demo-bucket"
REGION_NAME = "us-east-1"

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=REGION_NAME,
)

paginator = s3.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=BUCKET_NAME):
    for obj in page.get("Contents", []):
        print(obj["Key"])
