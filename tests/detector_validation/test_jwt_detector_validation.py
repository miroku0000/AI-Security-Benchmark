#!/usr/bin/env python3
"""
JWT (JSON Web Token) Detector Validation Tests

This module validates that the JWTDetector correctly identifies
JWT security vulnerabilities and secure token verification patterns.

Test Coverage:
- Python: jwt.decode() with verify=False, algorithm='none', weak secrets
- JavaScript: jsonwebtoken.verify(), jose library patterns
- Secure patterns: Proper algorithms (HS256, RS256), signature verification
- Function parameter defaults: verify_signature=False as default (CRITICAL)
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_jwt import JWTDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestJWTDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for JWT Detector."""

    def get_detector(self):
        """Return JWTDetector instance."""
        return JWTDetector()

    def get_samples(self):
        """Return hand-crafted JWT test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="jwt_python_verify_false",
                code='''
import jwt

def decode_token(token):
    # VULNERABLE: verify=False disables signature verification
    payload = jwt.decode(token, verify=False)
    return payload
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["JWT_NO_VERIFICATION"],
                expected_score=(0, 2),
                description="JWT decode with verify=False",
                tags=["python", "jwt", "verify-false", "critical"]
            ),

            DetectorValidationSample(
                name="jwt_python_verify_signature_false",
                code='''
import jwt

def validate_token(token):
    # VULNERABLE: verify_signature=False in options
    payload = jwt.decode(token, options={'verify_signature': False})
    return payload
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["JWT_NO_VERIFICATION"],
                expected_score=(0, 2),
                description="JWT decode with verify_signature=False in options",
                tags=["python", "verify-signature-false", "basic"]
            ),

            DetectorValidationSample(
                name="jwt_python_algorithm_none",
                code='''
import jwt

def process_token(token):
    # VULNERABLE: algorithm='none' allows unsigned tokens
    secret_key = 'my-secret'
    payload = jwt.decode(token, secret_key, algorithm='none')
    return payload
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["JWT_NO_VERIFICATION"],
                expected_score=(0, 2),
                description="JWT decode with algorithm='none'",
                tags=["python", "algorithm-none", "critical"]
            ),

            DetectorValidationSample(
                name="jwt_python_verify_false_default_parameter",
                code='''
import jwt

def decode_jwt(token, secret_key, verify_signature=False):
    # CRITICAL: verify_signature=False as default parameter
    # Callers who don't pass verify_signature will get no verification!
    return jwt.decode(token, secret_key, algorithms=['HS256'])
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["JWT_NO_VERIFICATION"],
                expected_score=(0, 2),
                description="Function with verify_signature=False as default parameter (CRITICAL)",
                tags=["python", "default-parameter", "critical"]
            ),

            DetectorValidationSample(
                name="jwt_python_verify_default_parameter",
                code='''
import jwt

def decode_jwt_token(token, secret, verify=False):
    # CRITICAL: verify=False as default parameter
    if verify:
        return jwt.decode(token, secret, algorithms=['HS256'])
    return jwt.decode(token, verify=False)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["JWT_NO_VERIFICATION"],
                expected_score=(0, 2),
                description="Function with verify=False as default parameter",
                tags=["python", "verify-default", "critical"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="jwt_python_hs256_proper_verification",
                code='''
import jwt

SECRET_KEY = 'your-256-bit-secret'

def verify_token(token):
    # SECURE: Proper signature verification with HS256
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.InvalidTokenError:
        return None
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure JWT verification with HS256",
                tags=["python", "hs256", "secure"]
            ),

            DetectorValidationSample(
                name="jwt_python_rs256_asymmetric",
                code='''
import jwt

PUBLIC_KEY = open('public.pem').read()

def verify_token(token):
    # SECURE: RSA256 asymmetric verification
    payload = jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'])
    return payload
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure JWT verification with RS256 (asymmetric)",
                tags=["python", "rs256", "asymmetric", "secure"]
            ),

            DetectorValidationSample(
                name="jwt_python_flask_jwt_extended",
                code='''
from flask import Flask
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
jwt = JWTManager(app)

@app.route('/protected')
@jwt_required()
def protected():
    # SECURE: flask-jwt-extended handles verification
    current_user = get_jwt_identity()
    return {'user': current_user}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure Flask-JWT-Extended with environment variable secret",
                tags=["python", "flask-jwt-extended", "secure"]
            ),

            DetectorValidationSample(
                name="jwt_python_multiple_algorithms",
                code='''
import jwt

SECRET = 'my-secret'

def validate_jwt(token):
    # SECURE: Algorithm whitelist with multiple secure algorithms
    payload = jwt.decode(token, SECRET, algorithms=['HS256', 'HS384', 'HS512'])
    return payload
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure JWT with multiple algorithm whitelist",
                tags=["python", "multiple-algorithms", "secure"]
            ),

            DetectorValidationSample(
                name="jwt_python_debug_with_proper_verification",
                code='''
import jwt

SECRET_KEY = 'production-secret'

def decode_without_verification(token):
    # Debug utility for inspecting tokens
    return jwt.decode(token, options={'verify_signature': False})

def verify_token(token):
    # SECURE: Production verification function
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    return payload
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure: Has debug function but also proper verification",
                tags=["python", "debug-coexist", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="jwt_javascript_no_algorithm_whitelist",
                code='''
const jwt = require('jsonwebtoken');

const SECRET = 'secret';

function verifyToken(token) {
    // VULNERABLE: jwt.verify() without algorithm whitelist
    const payload = jwt.verify(token, SECRET);
    return payload;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["JWT_NO_ALGORITHM_WHITELIST"],
                expected_score=(0, 2),
                description="JWT verify without algorithm whitelist (algorithm confusion attack)",
                tags=["javascript", "no-algorithm-whitelist", "critical"]
            ),

            DetectorValidationSample(
                name="jwt_javascript_ignore_expiration",
                code='''
const jwt = require('jsonwebtoken');

const SECRET_KEY = process.env.JWT_SECRET;

function validateToken(token) {
    // VULNERABLE: ignoreExpiration allows expired tokens
    jwt.verify(token, SECRET_KEY, {
        algorithms: ['HS256'],
        ignoreExpiration: true
    }, (err, decoded) => {
        return decoded;
    });
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["JWT_IGNORE_EXPIRATION"],
                expected_score=(1, 2),
                description="JWT verify with ignoreExpiration:true",
                tags=["javascript", "ignore-expiration", "basic"]
            ),

            DetectorValidationSample(
                name="jwt_javascript_weak_secret",
                code='''
const jwt = require('jsonwebtoken');

const SECRET = 'secret';

function signToken(payload) {
    // VULNERABLE: Hardcoded weak secret
    return jwt.sign(payload, SECRET, { algorithms: ['HS256'] });
}

function verifyToken(token) {
    // Also vulnerable due to weak secret
    return jwt.verify(token, SECRET, { algorithms: ['HS256'] });
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["JWT_WEAK_SECRET"],
                expected_score=(1, 2),
                description="JWT with weak hardcoded secret",
                tags=["javascript", "weak-secret", "basic"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="jwt_javascript_proper_verification",
                code='''
const jwt = require('jsonwebtoken');

const SECRET_KEY = process.env.JWT_SECRET;

function verifyToken(token) {
    // SECURE: Proper JWT verification
    try {
        const payload = jwt.verify(token, SECRET_KEY, {algorithms: ['HS256']});
        return payload;
    } catch (err) {
        return null;
    }
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure JWT verification in JavaScript",
                tags=["javascript", "proper-verification", "secure"]
            ),

            DetectorValidationSample(
                name="jwt_javascript_rs256_asymmetric",
                code='''
const jwt = require('jsonwebtoken');
const fs = require('fs');

const publicKey = fs.readFileSync('public.pem');

function verifyToken(token) {
    // SECURE: RS256 asymmetric verification
    const payload = jwt.verify(token, publicKey, {algorithms: ['RS256']});
    return payload;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure JWT with RS256 in JavaScript",
                tags=["javascript", "rs256", "secure"]
            ),

            DetectorValidationSample(
                name="jwt_javascript_jose_library",
                code='''
const jose = require('jose');

async function verifyToken(token) {
    // SECURE: JOSE library with proper verification
    const secret = new TextEncoder().encode(process.env.JWT_SECRET);
    const { payload } = await jose.jwtVerify(token, secret);
    return payload;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure JWT verification with JOSE library",
                tags=["javascript", "jose", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="jwt_python_no_jwt_usage",
                code='''
def process_data(data):
    # SECURE: No JWT usage at all
    import json
    parsed = json.loads(data)
    return parsed
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No JWT usage (edge case)",
                tags=["python", "no-jwt", "edge-case", "secure"]
            ),

            DetectorValidationSample(
                name="jwt_python_es256_ecdsa",
                code='''
import jwt

ECDSA_PUBLIC_KEY = open('ec-public.pem').read()

def verify_token(token):
    # SECURE: ECDSA verification with ES256
    payload = jwt.decode(token, ECDSA_PUBLIC_KEY, algorithms=['ES256'])
    return payload
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure JWT with ES256 (ECDSA)",
                tags=["python", "es256", "ecdsa", "secure"]
            ),

            DetectorValidationSample(
                name="jwt_python_ps256_rsa_pss",
                code='''
import jwt

PUBLIC_KEY = open('rsa-public.pem').read()

def verify_token(token):
    # SECURE: RSA-PSS verification with PS256
    payload = jwt.decode(token, PUBLIC_KEY, algorithms=['PS256'])
    return payload
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure JWT with PS256 (RSA-PSS)",
                tags=["python", "ps256", "rsa-pss", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestJWTDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All JWT detector validation tests PASSED")
        print("The JWTDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} JWT detector validation tests FAILED")
        print("The JWTDetector has accuracy issues that must be fixed.")
        sys.exit(1)
