#!/usr/bin/env python3
"""
Sensitive Logging Detector Validation Tests

This module validates that the SensitiveLoggingDetector correctly identifies
logging of sensitive information (passwords, tokens, API keys, PII).

Test Coverage:
- Python: Logging password with f-string interpolation (CRITICAL)
- Python: Logging token with print statement (CRITICAL)
- Python: Logging API key with string concatenation (CRITICAL)
- Python: Safe logging without sensitive data (SECURE)
- JavaScript: Logging password with template literal (CRITICAL)
- JavaScript: Logging API key with string concatenation (CRITICAL)
- JavaScript: Safe logging without sensitive data (SECURE)
- Edge cases: Logging text containing word "password" but not the value
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_sensitive_logging import SensitiveLoggingDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestSensitiveLoggingDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Sensitive Logging Detector."""

    def get_detector(self):
        """Return SensitiveLoggingDetector instance."""
        return SensitiveLoggingDetector()

    def get_samples(self):
        """Return hand-crafted sensitive logging test samples."""
        return [
            # ========== PYTHON - VULNERABLE - password logging ==========

            DetectorValidationSample(
                name="sensitive_logging_python_password",
                code='''
import logging

logger = logging.getLogger(__name__)

def login(username, password):
    logger.info(f"Login attempt: {username} with password {password}")
    authenticate(username, password)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SENSITIVE_DATA_LOGGING"],
                expected_score=(0, 2),
                description="Python logging password with f-string (CRITICAL)",
                tags=["python", "password", "critical"]
            ),

            # ========== PYTHON - VULNERABLE - token logging ==========

            DetectorValidationSample(
                name="sensitive_logging_python_token",
                code='''
def authenticate(token):
    print(f"Received token: {token}")
    validate_token(token)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SENSITIVE_DATA_LOGGING"],
                expected_score=(0, 2),
                description="Python logging token with print (CRITICAL)",
                tags=["python", "token", "critical"]
            ),

            # ========== PYTHON - SECURE - safe logging ==========

            DetectorValidationSample(
                name="sensitive_logging_python_safe",
                code='''
import logging

logger = logging.getLogger(__name__)

def login(username, password):
    logger.info(f"Login attempt for user: {username}")
    authenticate(username, password)
    logger.info("Authentication successful")
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Python safe logging without sensitive data (SECURE)",
                tags=["python", "safe", "secure"]
            ),

            DetectorValidationSample(
                name="sensitive_logging_python_safe_message",
                code='''
def process_data(data):
    logger.info("Processing data")
    result = transform(data)
    logger.info(f"Processed {len(result)} items")
    return result
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Python logging only counts and messages (SECURE)",
                tags=["python", "safe", "secure"]
            ),

            # ========== JAVASCRIPT - VULNERABLE - password logging ==========

            DetectorValidationSample(
                name="sensitive_logging_javascript_password",
                code='''
function login(username, password) {
    console.log(`Login attempt: ${username} with password ${password}`);
    authenticate(username, password);
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SENSITIVE_DATA_LOGGING"],
                expected_score=(0, 2),
                description="JavaScript logging password with template literal (CRITICAL)",
                tags=["javascript", "password", "critical"]
            ),

            # ========== JAVASCRIPT - VULNERABLE - API key logging ==========

            DetectorValidationSample(
                name="sensitive_logging_javascript_api_key",
                code='''
const apiKey = process.env.API_KEY;
console.log('Using API key: ' + apiKey);
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SENSITIVE_DATA_LOGGING"],
                expected_score=(0, 2),
                description="JavaScript logging API key with concatenation (CRITICAL)",
                tags=["javascript", "api_key", "critical"]
            ),

            # ========== JAVASCRIPT - VULNERABLE - token logging ==========

            DetectorValidationSample(
                name="sensitive_logging_javascript_token",
                code='''
function authenticate(token) {
    console.log(`Authenticating with token ${token}`);
    return validateToken(token);
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SENSITIVE_DATA_LOGGING"],
                expected_score=(0, 2),
                description="JavaScript logging token with template literal (CRITICAL)",
                tags=["javascript", "token", "critical"]
            ),

            # ========== JAVASCRIPT - SECURE - safe logging ==========

            DetectorValidationSample(
                name="sensitive_logging_javascript_safe",
                code='''
function login(username, password) {
    console.log('User login attempt:', username);
    console.log('Authentication in progress');
    authenticate(username, password);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="JavaScript safe logging without sensitive data (SECURE)",
                tags=["javascript", "safe", "secure"]
            ),

            DetectorValidationSample(
                name="sensitive_logging_javascript_safe_info",
                code='''
function processPayment(amount, creditCard) {
    console.log('Processing payment');
    console.log(`Amount: ${amount}`);
    chargeCard(creditCard, amount);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="JavaScript logging amount but not credit card (SECURE)",
                tags=["javascript", "safe", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="sensitive_logging_non_interpolated",
                code='''
def reset_password():
    logger.info("Password reset requested")
    logger.info("Sending password reset email")
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Logging word 'password' but not the value (SECURE)",
                tags=["python", "edge_case", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSensitiveLoggingDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Sensitive Logging detector validation tests PASSED")
        print("The SensitiveLoggingDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Sensitive Logging detector validation tests FAILED")
        print("The SensitiveLoggingDetector has accuracy issues that must be fixed.")
        sys.exit(1)
