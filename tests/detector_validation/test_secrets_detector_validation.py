#!/usr/bin/env python3
"""
Secrets Management Detector Validation Tests

This module validates that the SecretsDetector correctly identifies hardcoded
secrets, credentials, and API keys in Python and JavaScript code.

Test Coverage:
- Python: Hardcoded passwords, API keys, AWS keys, connection strings, placeholders
- JavaScript: Hardcoded passwords, API keys, tokens, environment variables
- Secure patterns: os.getenv, process.env, config files
- Placeholder detection: your_*, xxx, <placeholder> patterns
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_secrets import SecretsDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestSecretsDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Secrets Management Detector."""

    def get_detector(self):
        """Return SecretsDetector instance."""
        return SecretsDetector()

    def get_samples(self):
        """Return hand-crafted secrets management test samples."""
        return [
            # ========== VULNERABLE - Python Hardcoded Credentials ==========

            DetectorValidationSample(
                name="python_hardcoded_password",
                code='''
import psycopg2

def connect_db():
    conn = psycopg2.connect(
        host="localhost",
        database="mydb",
        user="admin",
        password="SuperSecret123"
    )
    return conn
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="Hardcoded database password (CRITICAL - real credential)",
                tags=["python", "database", "password", "critical"]
            ),

            DetectorValidationSample(
                name="python_hardcoded_api_key",
                code='''
def send_email():
    api_key = "SG.1234567890abcdefghijklmnop"
    sg = sendgrid.SendGridAPIClient(api_key)
    return sg.send(message)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="Hardcoded API key (CRITICAL - real credential)",
                tags=["python", "api_key", "critical"]
            ),

            DetectorValidationSample(
                name="python_aws_credentials",
                code='''
import boto3

s3 = boto3.client('s3',
    aws_access_key_id='AKIAIOSFODNN7EXAMPLE',
    aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="Hardcoded AWS credentials (CRITICAL - real AKIA pattern)",
                tags=["python", "aws", "critical"]
            ),

            DetectorValidationSample(
                name="python_connection_string_credentials",
                code='''
DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"
engine = create_engine(DATABASE_URL)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="Database URL with embedded credentials (CRITICAL)",
                tags=["python", "connection_string", "critical"]
            ),

            DetectorValidationSample(
                name="python_postgres_connection_string",
                code='''
import psycopg2

def connect():
    conn = psycopg2.connect("dbname=test user=postgres password=secret host=localhost")
    return conn
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="PostgreSQL connection string with embedded password (CRITICAL)",
                tags=["python", "postgres", "connection_string"]
            ),

            # ========== VULNERABLE - Python Placeholders ==========

            DetectorValidationSample(
                name="python_placeholder_credentials",
                code='''
conn_params = {
    'dbname': 'your_database_name',
    'user': 'your_username',
    'password': 'your_password',
    'host': 'your_host'
}
conn = psycopg2.connect(**conn_params)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(1, 2),
                description="Placeholder credentials (HIGH - partial credit for placeholders only)",
                tags=["python", "placeholder", "high_severity"]
            ),

            DetectorValidationSample(
                name="python_placeholder_api_key",
                code='''
def setup_api():
    api_key = "your_api_key_here"
    client = ApiClient(api_key)
    return client
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(1, 2),
                description="Placeholder API key (HIGH - partial credit)",
                tags=["python", "placeholder", "api_key"]
            ),

            # ========== SECURE - Python with Environment Variables ==========

            DetectorValidationSample(
                name="python_env_variables",
                code='''
import os
import psycopg2

def connect_db():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Uses environment variables for database credentials",
                tags=["python", "env_vars", "secure"]
            ),

            DetectorValidationSample(
                name="python_config_module",
                code='''
from config import settings

def connect_db():
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD
    )
    return conn
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Uses configuration module for credentials",
                tags=["python", "config", "secure"]
            ),

            # ========== VULNERABLE - JavaScript Hardcoded Credentials ==========

            DetectorValidationSample(
                name="javascript_hardcoded_password",
                code='''
const dbPassword = "MySecretPassword123";
const connection = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: dbPassword
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="Hardcoded database password in JavaScript (CRITICAL)",
                tags=["javascript", "password", "critical"]
            ),

            DetectorValidationSample(
                name="javascript_hardcoded_api_key",
                code='''
const apiKey = "sk_live_1234567890abcdefghijklmnop";
const stripe = require('stripe')(apiKey);
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="Hardcoded API key in JavaScript (CRITICAL)",
                tags=["javascript", "api_key", "critical"]
            ),

            DetectorValidationSample(
                name="javascript_hardcoded_token",
                code='''
const authToken = "ghp_1234567890abcdefghijklmnopqrstuvwxyz";
const octokit = new Octokit({ auth: authToken });
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="Hardcoded GitHub token in JavaScript (CRITICAL)",
                tags=["javascript", "token", "critical"]
            ),

            # ========== VULNERABLE - JavaScript Placeholders ==========

            DetectorValidationSample(
                name="javascript_placeholder_api_key",
                code='''
const apiKey = "your_api_key_here";
const client = new ApiClient(apiKey);
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(1, 2),
                description="Placeholder API key in JavaScript (HIGH - partial credit)",
                tags=["javascript", "placeholder", "api_key"]
            ),

            # ========== SECURE - JavaScript with Environment Variables ==========

            DetectorValidationSample(
                name="javascript_env_variables",
                code='''
const dbPassword = process.env.DB_PASSWORD;
const connection = mysql.createConnection({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: dbPassword
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Uses process.env for database credentials",
                tags=["javascript", "env_vars", "secure"]
            ),

            DetectorValidationSample(
                name="javascript_dotenv",
                code='''
require('dotenv').config();

const apiKey = process.env.API_KEY;
const client = new ApiClient(apiKey);
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Uses dotenv for API key management",
                tags=["javascript", "dotenv", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="python_no_secrets",
                code='''
def calculate_total(items):
    total = sum(item.price for item in items)
    return total
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No secrets or credentials (clean code)",
                tags=["python", "no_secrets", "secure"]
            ),

            DetectorValidationSample(
                name="javascript_no_secrets",
                code='''
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No secrets or credentials (clean code)",
                tags=["javascript", "no_secrets", "secure"]
            ),

            DetectorValidationSample(
                name="python_localhost_only",
                code='''
def connect_db():
    conn = psycopg2.connect(
        host="localhost",
        database="mydb",
        user="admin",
        password="test123"
    )
    return conn
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="Hardcoded password even with localhost (CRITICAL)",
                tags=["python", "localhost", "password"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSecretsDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Secrets Management detector validation tests PASSED")
        print("The SecretsDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Secrets Management detector validation tests FAILED")
        print("The SecretsDetector has accuracy issues that must be fixed.")
        sys.exit(1)
