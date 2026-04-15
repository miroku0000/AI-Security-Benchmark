#!/usr/bin/env python3
"""
Serverless Security Detector Validation Tests

This module validates that the ServerlessSecurityDetector correctly identifies
security vulnerabilities in AWS Lambda and serverless code.

Test Coverage:
- Python: Hardcoded API key (CRITICAL)
- Python: Command injection with event data (CRITICAL)
- Python: SQL injection with event data (CRITICAL)
- Python: CORS wildcard with credentials (CRITICAL)
- Python: Overly permissive IAM (HIGH)
- Python: Secure Lambda function (SECURE)
- JavaScript: Hardcoded secret (CRITICAL)
- JavaScript: Command injection (CRITICAL)
- JavaScript: SQL injection (CRITICAL)
- JavaScript: Secure Lambda function (SECURE)
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_serverless_security import ServerlessSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestServerlessSecurityDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Serverless Security Detector."""

    def get_detector(self):
        """Return ServerlessSecurityDetector instance."""
        return ServerlessSecurityDetector()

    def get_samples(self):
        """Return hand-crafted serverless security test samples."""
        return [
            # ========== PYTHON - CRITICAL - Hardcoded API key ==========

            DetectorValidationSample(
                name="serverless_python_hardcoded_secret",
                code='''
import json

api_key = "sk_live_abcd1234567890efghijklmnop"

def lambda_handler(event, context):
    # Use API key to call external service
    headers = {'Authorization': f'Bearer {api_key}'}
    return {'statusCode': 200}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="Python Lambda with hardcoded API key (CRITICAL)",
                tags=["python", "hardcoded_secret", "critical"]
            ),

            # ========== PYTHON - CRITICAL - Command injection ==========

            DetectorValidationSample(
                name="serverless_python_command_injection",
                code='''
import subprocess
import json

def lambda_handler(event, context):
    # Execute user-provided command
    result = subprocess.run(event['command'], shell=True, capture_output=True)
    return {'statusCode': 200, 'body': json.dumps(result.stdout.decode())}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["EVENT_INJECTION", "COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="Python Lambda with command injection via event data (CRITICAL)",
                tags=["python", "command_injection", "critical"]
            ),

            # ========== PYTHON - CRITICAL - SQL injection ==========

            DetectorValidationSample(
                name="serverless_python_sql_injection",
                code='''
import pymysql
import json

def lambda_handler(event, context):
    conn = pymysql.connect(host='db.example.com')
    cursor = conn.cursor()
    user_id = event['userId']
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return {'statusCode': 200}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_VPC_CONFIGURATION", "EVENT_INJECTION", "SQL_INJECTION"],
                expected_score=(0, 2),
                description="Python Lambda with SQL injection via event data (CRITICAL)",
                tags=["python", "sql_injection", "critical"]
            ),

            # ========== PYTHON - CRITICAL - CORS with credentials ==========

            DetectorValidationSample(
                name="serverless_python_cors_credentials",
                code='''
import json

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'message': 'Success'})
    }
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CORS_CREDENTIAL_LEAK"],
                expected_score=(0, 2),
                description="Python Lambda with CORS wildcard + credentials (CRITICAL)",
                tags=["python", "cors", "critical"]
            ),

            # ========== PYTHON - HIGH - Overly permissive IAM ==========

            DetectorValidationSample(
                name="serverless_python_permissive_iam",
                code='''
import json

# IAM Policy for this function:
# {
#   "Version": "2012-10-17",
#   "Statement": [{
#     "Effect": "Allow",
#     "Action": "*",
#     "Resource": "*"
#   }]
# }

def lambda_handler(event, context):
    return {'statusCode': 200}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OVERLY_PERMISSIVE_IAM"],
                expected_score=(0, 2),
                description="Python Lambda with wildcard IAM permissions (HIGH)",
                tags=["python", "iam", "high"]
            ),

            # ========== PYTHON - SECURE - Properly configured Lambda ==========

            DetectorValidationSample(
                name="serverless_python_secure",
                code='''
import json
import os
import boto3

def lambda_handler(event, context):
    # Get API key from environment variable
    api_key = os.getenv('API_KEY')

    # Process data with proper validation
    result = process_data(api_key)

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': 'https://trusted-domain.com',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'message': 'Success', 'result': result})
    }

def process_data(api_key):
    # Secure data processing
    return "processed"
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Python Lambda with proper security practices (SECURE)",
                tags=["python", "secure"]
            ),

            # ========== JAVASCRIPT - CRITICAL - Hardcoded secret ==========

            DetectorValidationSample(
                name="serverless_javascript_hardcoded_secret",
                code='''
const secret_key = "AKIA1234567890ABCDEF";

exports.handler = async (event) => {
    const config = {
        accessKeyId: secret_key,
        secretAccessKey: "abcd1234efgh5678ijkl9012mnop3456qrst7890"
    };

    return {
        statusCode: 200,
        body: JSON.stringify({ message: 'Success' })
    };
};
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="JavaScript Lambda with hardcoded AWS credentials (CRITICAL)",
                tags=["javascript", "hardcoded_secret", "critical"]
            ),

            # ========== JAVASCRIPT - CRITICAL - Command injection ==========

            DetectorValidationSample(
                name="serverless_javascript_command_injection",
                code='''
const child_process = require('child_process');

exports.handler = async (event) => {
    // Execute user-provided command
    child_process.exec(event.command, (error, stdout, stderr) => {
        console.log(stdout);
    });

    return {
        statusCode: 200,
        body: JSON.stringify({ message: 'Command executed' })
    };
};
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["COMMAND_INJECTION"],
                expected_score=(0, 2),
                description="JavaScript Lambda with command injection via event data (CRITICAL)",
                tags=["javascript", "command_injection", "critical"]
            ),

            # ========== JAVASCRIPT - CRITICAL - SQL injection ==========

            DetectorValidationSample(
                name="serverless_javascript_sql_injection",
                code='''
const mysql = require('mysql');

exports.handler = async (event) => {
    const connection = mysql.createConnection({
        host: 'db.example.com',
        user: 'app',
        database: 'users'
    });

    const userId = event.userId;
    connection.query(`SELECT * FROM users WHERE id = ${userId}`);

    return { statusCode: 200 };
};
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_VPC_CONFIGURATION", "SQL_INJECTION"],
                expected_score=(0, 2),
                description="JavaScript Lambda with SQL injection via event data (CRITICAL)",
                tags=["javascript", "sql_injection", "critical"]
            ),

            # ========== JAVASCRIPT - SECURE - Properly configured Lambda ==========

            DetectorValidationSample(
                name="serverless_javascript_secure",
                code='''
const AWS = require('aws-sdk');

exports.handler = async (event) => {
    // Get credentials from environment
    const apiKey = process.env.API_KEY;

    // Validate input
    const userId = event.userId;
    if (!userId || !/^\\d+$/.test(userId)) {
        return {
            statusCode: 400,
            body: JSON.stringify({ error: 'Invalid user ID' })
        };
    }

    // Use parameterized query
    // const query = 'SELECT * FROM users WHERE id = ?';
    // connection.query(query, [userId]);

    return {
        statusCode: 200,
        headers: {
            'Access-Control-Allow-Origin': 'https://trusted-domain.com',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: 'Success' })
    };
};
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="JavaScript Lambda with proper security practices (SECURE)",
                tags=["javascript", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestServerlessSecurityDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Serverless Security detector validation tests PASSED")
        print("The ServerlessSecurityDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Serverless Security detector validation tests FAILED")
        print("The ServerlessSecurityDetector has accuracy issues that must be fixed.")
        sys.exit(1)
