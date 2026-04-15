#!/usr/bin/env python3
"""
Insecure Authentication Detector Validation Tests

This module validates that the InsecureAuthDetector correctly identifies
authentication and session management vulnerabilities.

Test Coverage:
- Python: Token generation (random vs secrets), password hashing (SHA vs bcrypt),
  session security, JWT expiration, password validation, rate limiting
- JavaScript: Math.random() vs crypto.randomBytes(), password hashing,
  session cookies, JWT expiration, credentials in cookies
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_insecure_auth import InsecureAuthDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestInsecureAuthDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Insecure Authentication Detector."""

    def get_detector(self):
        """Return InsecureAuthDetector instance."""
        return InsecureAuthDetector()

    def get_samples(self):
        """Return hand-crafted insecure authentication test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python Token Generation ==========

            DetectorValidationSample(
                name="auth_python_weak_random_token",
                code='''
import random
import string

def generate_token():
    # VULNERABLE: Uses non-cryptographic random module
    characters = string.ascii_letters + string.digits
    token = ''.join(random.choice(characters) for _ in range(32))
    return token
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_TOKEN_GENERATION"],
                expected_score=(0, 2),
                description="Weak token generation using random module",
                tags=["python", "token", "weak-random", "critical"]
            ),

            DetectorValidationSample(
                name="auth_python_timestamp_token",
                code='''
import time
import hashlib

def generate_auth_token(user_id):
    # VULNERABLE: Predictable timestamp-based token
    timestamp = str(time.time())
    token = hashlib.sha256(f"{user_id}{timestamp}".encode()).hexdigest()
    return token
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PREDICTABLE_TOKEN"],
                expected_score=(0, 2),
                description="Predictable token based on timestamp",
                tags=["python", "token", "timestamp", "predictable"]
            ),

            DetectorValidationSample(
                name="auth_python_static_token",
                code='''
def create_session_token(user):
    # VULNERABLE: Static hardcoded token
    token = "abc123xyz789"
    return token
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["STATIC_TOKEN"],
                expected_score=(0, 2),
                description="Static/hardcoded token value",
                tags=["python", "token", "static", "critical"]
            ),

            # ========== SECURE SAMPLES - Python Token Generation ==========

            DetectorValidationSample(
                name="auth_python_secrets_token",
                code='''
import secrets

def generate_token():
    # SECURE: Uses secrets module for cryptographic randomness
    token = secrets.token_urlsafe(32)
    return token
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure token with secrets module",
                tags=["python", "token", "secrets", "secure"]
            ),

            DetectorValidationSample(
                name="auth_python_os_urandom_token",
                code='''
import os
import base64

def make_auth_token():
    # SECURE: Uses os.urandom() for secure randomness
    random_bytes = os.urandom(32)
    token = base64.urlsafe_b64encode(random_bytes).decode('utf-8')
    return token
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure token with os.urandom()",
                tags=["python", "token", "urandom", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - Python Password Hashing ==========

            DetectorValidationSample(
                name="auth_python_sha256_password",
                code='''
import hashlib

def hash_password(password):
    # VULNERABLE: Fast hash (SHA256) for passwords
    return hashlib.sha256(password.encode()).hexdigest()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_PASSWORD_HASHING"],
                expected_score=(0, 2),
                description="Weak password hashing with SHA256",
                tags=["python", "password", "sha256", "critical"]
            ),

            DetectorValidationSample(
                name="auth_python_md5_password",
                code='''
import hashlib

def store_password(password):
    # VULNERABLE: MD5 for password hashing
    password_hash = hashlib.md5(password.encode()).hexdigest()
    return password_hash
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_PASSWORD_HASHING"],
                expected_score=(0, 2),
                description="Weak password hashing with MD5",
                tags=["python", "password", "md5", "critical"]
            ),

            # ========== SECURE SAMPLES - Python Password Hashing ==========

            DetectorValidationSample(
                name="auth_python_bcrypt_password",
                code='''
import bcrypt

def hash_password(password):
    # SECURE: Uses bcrypt for password hashing
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure password hashing with bcrypt",
                tags=["python", "password", "bcrypt", "secure"]
            ),

            DetectorValidationSample(
                name="auth_python_argon2_password",
                code='''
from argon2 import PasswordHasher

def hash_password(password):
    # SECURE: Uses argon2 for password hashing
    ph = PasswordHasher()
    hash = ph.hash(password)
    return hash
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure password hashing with argon2",
                tags=["python", "password", "argon2", "secure"]
            ),

            DetectorValidationSample(
                name="auth_python_pbkdf2_password",
                code='''
import hashlib

def hash_password(password, salt):
    # SECURE: Uses PBKDF2 for password hashing
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return dk
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure password hashing with PBKDF2",
                tags=["python", "password", "pbkdf2", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - Python Session/JWT ==========

            DetectorValidationSample(
                name="auth_python_jwt_no_expiration",
                code='''
import jwt

SECRET_KEY = 'secret-key'

def get_user_jwt(user_id):
    # VULNERABLE: JWT never expires
    payload = {'user_id': user_id}
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["JWT_NO_EXPIRATION"],
                expected_score=(0, 2),
                description="JWT without expiration time",
                tags=["python", "jwt", "no-expiration", "high"]
            ),

            DetectorValidationSample(
                name="auth_python_session_no_httponly",
                code='''
from flask import Flask, session

app = Flask(__name__)
app.config['SESSION_COOKIE_SECURE'] = True
# VULNERABLE: Missing HttpOnly flag

@app.route('/login')
def login():
    session['user_id'] = 123
    return 'Logged in'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_SESSION"],
                expected_score=(1, 2),
                description="Session cookie without HttpOnly flag",
                tags=["python", "session", "no-httponly", "medium"]
            ),

            DetectorValidationSample(
                name="auth_python_session_no_secure",
                code='''
from flask import Flask, session

app = Flask(__name__)
app.config['SESSION_COOKIE_HTTPONLY'] = True
# VULNERABLE: Missing Secure flag

@app.route('/login')
def login():
    session['user_id'] = 123
    return 'Logged in'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_SESSION"],
                expected_score=(1, 2),
                description="Session cookie without Secure flag",
                tags=["python", "session", "no-secure", "medium"]
            ),

            # ========== SECURE SAMPLES - Python Session/JWT ==========

            DetectorValidationSample(
                name="auth_python_jwt_with_expiration",
                code='''
import jwt
from datetime import datetime, timedelta

SECRET_KEY = 'secret-key'

def get_user_jwt(user_id):
    # SECURE: JWT with exp claim
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="JWT with expiration time",
                tags=["python", "jwt", "expiration", "secure"]
            ),

            DetectorValidationSample(
                name="auth_python_session_secure_config",
                code='''
from flask import Flask, session

app = Flask(__name__)
# SECURE: All security flags enabled
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'

@app.route('/login')
def login():
    session['user_id'] = 123
    return 'Logged in'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["NO_RATE_LIMITING"],
                expected_score=(1, 2),
                description="Secure session cookie configuration (but no rate limiting on login)",
                tags=["python", "session", "all-flags", "partial"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript Token Generation ==========

            DetectorValidationSample(
                name="auth_javascript_math_random_token",
                code='''
function generateToken(length) {
    // VULNERABLE: Uses Math.random() (not cryptographically secure)
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let token = '';
    for (let i = 0; i < length; i++) {
        token += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return token;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_TOKEN_GENERATION"],
                expected_score=(0, 2),
                description="Weak token with Math.random() in JavaScript",
                tags=["javascript", "token", "math-random", "critical"]
            ),

            DetectorValidationSample(
                name="auth_javascript_timestamp_token",
                code='''
function createAuthToken(userId) {
    // VULNERABLE: Timestamp-based token
    const timestamp = Date.now();
    const token = userId + '_' + timestamp;
    return token;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PREDICTABLE_TOKEN"],
                expected_score=(0, 2),
                description="Predictable timestamp-based token in JavaScript",
                tags=["javascript", "token", "timestamp", "predictable"]
            ),

            # ========== SECURE SAMPLES - JavaScript Token Generation ==========

            DetectorValidationSample(
                name="auth_javascript_crypto_randombytes",
                code='''
const crypto = require('crypto');

function generateToken(length) {
    // SECURE: Uses crypto.randomBytes()
    return crypto.randomBytes(length).toString('hex');
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure token with crypto.randomBytes()",
                tags=["javascript", "token", "crypto", "secure"]
            ),

            DetectorValidationSample(
                name="auth_javascript_crypto_randomuuid",
                code='''
const crypto = require('crypto');

function makeToken() {
    // SECURE: Uses crypto.randomUUID()
    return crypto.randomUUID();
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure token with crypto.randomUUID()",
                tags=["javascript", "token", "uuid", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript Password Hashing ==========

            DetectorValidationSample(
                name="auth_javascript_sha256_password",
                code='''
const crypto = require('crypto');

function hashPassword(password) {
    // VULNERABLE: Fast hash (SHA256) for passwords
    return crypto.createHash('sha256').update(password).digest('hex');
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_PASSWORD_HASHING"],
                expected_score=(0, 2),
                description="Weak password hashing with SHA256 in JavaScript",
                tags=["javascript", "password", "sha256", "critical"]
            ),

            DetectorValidationSample(
                name="auth_javascript_md5_password",
                code='''
const crypto = require('crypto');

function hashPassword(password) {
    // VULNERABLE: MD5 for password hashing
    const hash = crypto.createHash('md5').update(password).digest('hex');
    return hash;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_PASSWORD_HASHING"],
                expected_score=(0, 2),
                description="Weak password hashing with MD5 in JavaScript",
                tags=["javascript", "password", "md5", "critical"]
            ),

            # ========== SECURE SAMPLES - JavaScript Password Hashing ==========

            DetectorValidationSample(
                name="auth_javascript_bcrypt_password",
                code='''
const bcrypt = require('bcrypt');

async function hashPassword(password) {
    // SECURE: Uses bcrypt for password hashing
    const saltRounds = 10;
    const hash = await bcrypt.hash(password, saltRounds);
    return hash;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure password hashing with bcrypt in JavaScript",
                tags=["javascript", "password", "bcrypt", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript JWT/Session ==========

            DetectorValidationSample(
                name="auth_javascript_jwt_no_expiration",
                code='''
const jwt = require('jsonwebtoken');

function createToken(userId) {
    // VULNERABLE: JWT never expires
    const payload = { userId: userId };
    const token = jwt.sign(payload, 'secret-key');
    return token;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["JWT_NO_EXPIRATION"],
                expected_score=(0, 2),
                description="JWT without expiration in JavaScript",
                tags=["javascript", "jwt", "no-expiration", "high"]
            ),

            DetectorValidationSample(
                name="auth_javascript_credentials_in_cookie",
                code='''
function rememberMe(username, password) {
    // VULNERABLE: Storing password in cookie
    document.cookie = `passwordHash=${password}; max-age=604800`;
    document.cookie = `username=${username}; max-age=604800`;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CREDENTIALS_IN_COOKIE"],
                expected_score=(0, 2),
                description="Storing credentials in client-side cookie",
                tags=["javascript", "cookie", "credentials", "critical"]
            ),

            # ========== SECURE SAMPLES - JavaScript JWT ==========

            DetectorValidationSample(
                name="auth_javascript_jwt_with_expiration",
                code='''
const jwt = require('jsonwebtoken');

function createToken(userId) {
    // SECURE: JWT with expiresIn option
    const payload = { userId: userId };
    const token = jwt.sign(payload, 'secret-key', { expiresIn: '1h' });
    return token;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="JWT with expiration in JavaScript",
                tags=["javascript", "jwt", "expiration", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="auth_python_no_auth_code",
                code='''
def process_data(data):
    # SECURE: No authentication code to analyze
    result = data.upper()
    return result
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No authentication code (edge case)",
                tags=["python", "no-auth", "edge-case", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInsecureAuthDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Insecure Authentication detector validation tests PASSED")
        print("The InsecureAuthDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Insecure Authentication detector validation tests FAILED")
        print("The InsecureAuthDetector has accuracy issues that must be fixed.")
        sys.exit(1)
