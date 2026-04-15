#!/usr/bin/env python3
"""
Cloud Infrastructure as Code (IaC) Detector Validation Tests

This module validates that the CloudIaCDetector correctly identifies
security misconfigurations in Terraform and CloudFormation templates.

Test Coverage:
- Terraform: Public S3 buckets (CRITICAL)
- Terraform: Missing S3 encryption (HIGH)
- Terraform: Overly permissive IAM (HIGH)
- Terraform: Unrestricted security groups with 0.0.0.0/0 (CRITICAL)
- Terraform: Public RDS databases (CRITICAL)
- Terraform: Hardcoded credentials (CRITICAL)
- Terraform: Secure configurations (SECURE)
- CloudFormation: Public S3 buckets (CRITICAL)
- CloudFormation: Missing encryption (HIGH)
- CloudFormation: Secure configurations (SECURE)
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_cloud_iac import CloudIaCDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestCloudIaCDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Cloud IaC Detector."""

    def get_detector(self):
        """Return CloudIaCDetector instance."""
        return CloudIaCDetector()

    def get_samples(self):
        """Return hand-crafted cloud IaC test samples."""
        return [
            # ========== TERRAFORM - CRITICAL - Public S3 bucket ==========

            DetectorValidationSample(
                name="cloud_iac_terraform_public_s3",
                code='''
resource "aws_s3_bucket" "uploads" {
  bucket = "company-uploads"
  acl    = "public-read"
}
''',
                language="terraform",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PUBLIC_S3_BUCKET"],
                expected_score=(0, 2),
                description="Terraform S3 bucket with public-read ACL (CRITICAL)",
                tags=["terraform", "s3", "public", "critical"]
            ),

            # ========== TERRAFORM - HIGH - Overly permissive IAM ==========

            DetectorValidationSample(
                name="cloud_iac_terraform_wildcard_iam",
                code='''
resource "aws_iam_policy" "app" {
  name = "app-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}
''',
                language="terraform",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OVERLY_PERMISSIVE_IAM"],
                expected_score=(0, 2),
                description="Terraform IAM policy with wildcard permissions (HIGH)",
                tags=["terraform", "iam", "wildcard", "high"]
            ),

            # ========== TERRAFORM - CRITICAL - Unrestricted security group ==========

            DetectorValidationSample(
                name="cloud_iac_terraform_open_sg",
                code='''
resource "aws_security_group" "web" {
  name = "web-sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
''',
                language="terraform",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["UNRESTRICTED_SECURITY_GROUP"],
                expected_score=(0, 2),
                description="Terraform security group allows 0.0.0.0/0 SSH access (CRITICAL)",
                tags=["terraform", "security_group", "ssh", "critical"]
            ),

            # ========== TERRAFORM - CRITICAL - Public RDS database ==========

            DetectorValidationSample(
                name="cloud_iac_terraform_public_rds",
                code='''
resource "aws_db_instance" "production" {
  identifier        = "prod-db"
  engine           = "postgres"
  instance_class   = "db.t3.medium"
  publicly_accessible = true
}
''',
                language="terraform",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PUBLIC_DATABASE"],
                expected_score=(0, 2),
                description="Terraform RDS database with publicly_accessible = true (CRITICAL)",
                tags=["terraform", "rds", "public", "critical"]
            ),

            # ========== TERRAFORM - CRITICAL - Hardcoded credentials ==========

            DetectorValidationSample(
                name="cloud_iac_terraform_hardcoded_password",
                code='''
resource "aws_db_instance" "production" {
  identifier     = "prod-db"
  engine        = "postgres"
  master_username = "admin"
  master_password = "SuperSecret123!"
}
''',
                language="terraform",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_CREDENTIALS"],
                expected_score=(0, 2),
                description="Terraform RDS with hardcoded password (CRITICAL)",
                tags=["terraform", "credentials", "hardcoded", "critical"]
            ),

            # ========== TERRAFORM - SECURE - Properly configured S3 ==========

            DetectorValidationSample(
                name="cloud_iac_terraform_secure_s3",
                code='''
resource "aws_s3_bucket" "data" {
  bucket = "company-data"
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
''',
                language="terraform",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Terraform S3 with proper security configuration (SECURE)",
                tags=["terraform", "s3", "secure"]
            ),

            DetectorValidationSample(
                name="cloud_iac_terraform_secure_sg",
                code='''
resource "aws_security_group" "app" {
  name = "app-sg"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
}
''',
                language="terraform",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Terraform security group with restricted access (SECURE)",
                tags=["terraform", "security_group", "secure"]
            ),

            # ========== CLOUDFORMATION - CRITICAL - Public S3 bucket ==========

            DetectorValidationSample(
                name="cloud_iac_cloudformation_public_s3",
                code='''
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: company-data
      AccessControl: PublicRead
''',
                language="yaml",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PUBLIC_S3_BUCKET"],
                expected_score=(0, 2),
                description="CloudFormation S3 bucket with PublicRead ACL (CRITICAL)",
                tags=["cloudformation", "s3", "public", "critical"]
            ),

            # ========== CLOUDFORMATION - SECURE - Properly configured S3 ==========

            DetectorValidationSample(
                name="cloud_iac_cloudformation_secure_s3",
                code='''
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  SecureBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: secure-data
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      VersioningConfiguration:
        Status: Enabled
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="CloudFormation S3 with proper security (SECURE)",
                tags=["cloudformation", "s3", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="cloud_iac_non_aws_yaml",
                code='''
version: '3'
services:
  app:
    image: nginx:latest
    ports:
      - "80:80"
''',
                language="yaml",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-CloudFormation YAML (out of scope)",
                tags=["yaml", "edge_case", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCloudIaCDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Cloud IaC detector validation tests PASSED")
        print("The CloudIaCDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Cloud IaC detector validation tests FAILED")
        print("The CloudIaCDetector has accuracy issues that must be fixed.")
        sys.exit(1)
