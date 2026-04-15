#!/usr/bin/env python3
"""
Error Handling Detector Validation Tests

This module validates that the ErrorHandlingDetector correctly identifies
missing error handling in Python and JavaScript code.

Test Coverage:
- Python: DB ops, file ops, network ops, subprocess, JSON parsing, try/except
- JavaScript: callbacks, promises, async/await, JSON.parse, fs ops
- Secure patterns: try/except, context managers, if(err), .catch()
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_error_handling import ErrorHandlingDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestErrorHandlingDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Error Handling Detector."""

    def get_detector(self):
        """Return ErrorHandlingDetector instance."""
        return ErrorHandlingDetector()

    def get_samples(self):
        """Return hand-crafted error handling test samples."""
        return [
            # ========== VULNERABLE - Python Database Operations ==========

            DetectorValidationSample(
                name="python_db_no_error_handling",
                code='''
import psycopg2

def get_user(user_id):
    conn = psycopg2.connect(dbname='mydb')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING"],
                expected_score=(0, 2),
                description="Database operations without try/except",
                tags=["python", "database", "missing_try_except"]
            ),

            # ========== SECURE - Python Database with try/except ==========

            DetectorValidationSample(
                name="python_db_with_try_except",
                code='''
import psycopg2

def get_user(user_id):
    try:
        conn = psycopg2.connect(dbname='mydb')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except psycopg2.Error as e:
        print(f"DB error: {e}")
        return None
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with try/except for DB operations",
                tags=["python", "database", "try_except", "secure"]
            ),

            # ========== SECURE - Python with context manager ==========

            DetectorValidationSample(
                name="python_context_manager",
                code='''
import psycopg2

def get_user(user_id):
    with psycopg2.connect(dbname='mydb') as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING", "SECURE"],
                expected_score=(1, 2),
                description="Partial protection with context managers (handles cleanup, not exceptions)",
                tags=["python", "context_manager", "partial"]
            ),

            # ========== VULNERABLE - Python File Operations ==========

            DetectorValidationSample(
                name="python_file_no_error_handling",
                code='''
def read_config(filename):
    f = open(filename, 'r')
    data = f.read()
    f.close()
    return data
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING"],
                expected_score=(0, 2),
                description="File operations without error handling",
                tags=["python", "file", "missing_error_handling"]
            ),

            # ========== VULNERABLE - Python Network Operations ==========

            DetectorValidationSample(
                name="python_network_no_error_handling",
                code='''
import requests

def fetch_data(url):
    response = requests.get(url)
    return response.json()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING"],
                expected_score=(0, 2),
                description="Network operations without error handling",
                tags=["python", "network", "requests"]
            ),

            # ========== VULNERABLE - Python subprocess ==========

            DetectorValidationSample(
                name="python_subprocess_no_error_handling",
                code='''
import subprocess

def convert_image(input_file):
    subprocess.run(['convert', input_file, 'output.png'])
    return 'output.png'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING"],
                expected_score=(0, 2),
                description="Subprocess operations without error handling",
                tags=["python", "subprocess"]
            ),

            # ========== VULNERABLE - Python JSON parsing ==========

            DetectorValidationSample(
                name="python_json_no_error_handling",
                code='''
import json

def parse_data(json_str):
    data = json.loads(json_str)
    return data['user_id']
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING"],
                expected_score=(1, 2),
                description="JSON parsing without error handling (LOW severity)",
                tags=["python", "json", "low_severity"]
            ),

            # ========== VULNERABLE - JavaScript callback no error check ==========

            DetectorValidationSample(
                name="javascript_callback_no_err_check",
                code='''
db.query('SELECT * FROM users WHERE id = ?', [userId], (err, results) => {
    res.json(results);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING"],
                expected_score=(0, 2),
                description="Callback receives err but doesn't check it",
                tags=["javascript", "callback", "missing_if_err"]
            ),

            # ========== SECURE - JavaScript callback with error check ==========

            DetectorValidationSample(
                name="javascript_callback_with_err_check",
                code='''
db.query('SELECT * FROM users WHERE id = ?', [userId], (err, results) => {
    if (err) {
        return res.status(500).json({error: 'DB error'});
    }
    res.json(results);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure with if(err) check in callback",
                tags=["javascript", "callback", "if_err", "secure"]
            ),

            # ========== VULNERABLE - JavaScript promise without catch ==========

            DetectorValidationSample(
                name="javascript_promise_no_catch",
                code='''
fetchUserData(userId)
    .then(data => {
        res.json(data);
    });
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING"],
                expected_score=(0, 2),
                description="Promise without .catch() handler",
                tags=["javascript", "promise", "missing_catch"]
            ),

            # ========== SECURE - JavaScript promise with catch ==========

            DetectorValidationSample(
                name="javascript_promise_with_catch",
                code='''
fetchUserData(userId)
    .then(data => {
        res.json(data);
    })
    .catch(err => {
        res.status(500).json({error: 'Failed'});
    });
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure with .catch() handler",
                tags=["javascript", "promise", "catch", "secure"]
            ),

            # ========== VULNERABLE - JavaScript async/await no try/catch ==========

            DetectorValidationSample(
                name="javascript_async_await_no_try_catch",
                code='''
async function getUserData(userId) {
    const user = await db.query('SELECT * FROM users WHERE id = ?', [userId]);
    return user;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING"],
                expected_score=(0, 2),
                description="Async/await without try/catch block",
                tags=["javascript", "async_await", "missing_try_catch"]
            ),

            # ========== SECURE - JavaScript async/await with try/catch ==========

            DetectorValidationSample(
                name="javascript_async_await_with_try_catch",
                code='''
async function getUserData(userId) {
    try {
        const user = await db.query('SELECT * FROM users WHERE id = ?', [userId]);
        return user;
    } catch (err) {
        console.error('DB error:', err);
        throw new Error('Failed to get user');
    }
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure with try/catch for async/await",
                tags=["javascript", "async_await", "try_catch", "secure"]
            ),

            # ========== VULNERABLE - JavaScript JSON.parse no try/catch ==========

            DetectorValidationSample(
                name="javascript_json_parse_no_try_catch",
                code='''
function parseUserData(jsonString) {
    const data = JSON.parse(jsonString);
    return data.userId;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING"],
                expected_score=(1, 2),
                description="JSON.parse without try/catch (LOW severity)",
                tags=["javascript", "json_parse", "low_severity"]
            ),

            # ========== VULNERABLE - JavaScript fs operations ==========

            DetectorValidationSample(
                name="javascript_fs_no_error_handling",
                code='''
function readConfig(filename) {
    const data = fs.readFileSync(filename, 'utf8');
    return JSON.parse(data);
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_ERROR_HANDLING"],
                expected_score=(0, 2),
                description="File system operations without error handling",
                tags=["javascript", "fs", "readFileSync"]
            ),

            # ========== EDGE CASE - No risky operations ==========

            DetectorValidationSample(
                name="python_no_risky_operations",
                code='''
def calculate_total(items):
    total = sum(item.price for item in items)
    return total
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No risky operations (no error handling needed)",
                tags=["python", "no_risky_ops", "secure"]
            ),

            DetectorValidationSample(
                name="javascript_no_risky_operations",
                code='''
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No risky operations (no error handling needed)",
                tags=["javascript", "no_risky_ops", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestErrorHandlingDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Error Handling detector validation tests PASSED")
        print("The ErrorHandlingDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Error Handling detector validation tests FAILED")
        print("The ErrorHandlingDetector has accuracy issues that must be fixed.")
        sys.exit(1)
