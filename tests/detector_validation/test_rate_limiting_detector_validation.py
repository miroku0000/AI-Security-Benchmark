#!/usr/bin/env python3
"""
Rate Limiting Detector Validation Tests

This module validates that the RateLimitingDetector correctly identifies
missing rate limiting in Flask, Express, and Django applications.

Test Coverage:
- Python: Flask authentication endpoints, sensitive endpoints, public endpoints
- JavaScript: Express authentication endpoints, sensitive endpoints, public endpoints
- Django: REST Framework APIView classes with/without throttling
- Secure patterns: @limiter.limit, express-rate-limit, throttle_classes
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_rate_limiting import RateLimitingDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestRateLimitingDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Rate Limiting Detector."""

    def get_detector(self):
        """Return RateLimitingDetector instance."""
        return RateLimitingDetector()

    def get_samples(self):
        """Return hand-crafted rate limiting test samples."""
        return [
            # ========== VULNERABLE - Flask Authentication Endpoints ==========

            DetectorValidationSample(
                name="flask_login_no_rate_limit",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    # authenticate user
    return 'OK'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_RATE_LIMITING_AUTH"],
                expected_score=(0, 2),
                description="Flask login endpoint without rate limiting (CRITICAL)",
                tags=["python", "flask", "authentication", "critical"]
            ),

            DetectorValidationSample(
                name="flask_register_no_rate_limit",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    # create user
    return 'OK'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_RATE_LIMITING_AUTH"],
                expected_score=(0, 2),
                description="Flask register endpoint without rate limiting (CRITICAL)",
                tags=["python", "flask", "authentication", "register"]
            ),

            # ========== SECURE - Flask with Rate Limiting ==========

            DetectorValidationSample(
                name="flask_login_with_rate_limit",
                code='''
from flask import Flask, request
from flask_limiter import Limiter

app = Flask(__name__)
limiter = Limiter(app)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    # authenticate user
    return 'OK'
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Flask login endpoint with rate limiting",
                tags=["python", "flask", "authentication", "secure"]
            ),

            # ========== VULNERABLE - Flask Sensitive Endpoints ==========

            DetectorValidationSample(
                name="flask_search_no_rate_limit",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/api/search')
def search():
    query = request.args.get('q')
    results = expensive_search(query)
    return jsonify(results)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_RATE_LIMITING"],
                expected_score=(1, 2),
                description="Flask search endpoint without rate limiting (MEDIUM)",
                tags=["python", "flask", "sensitive", "search"]
            ),

            # ========== VULNERABLE - Flask Public Endpoints ==========

            DetectorValidationSample(
                name="flask_public_no_rate_limit",
                code='''
from flask import Flask

app = Flask(__name__)

@app.route('/about')
def about():
    return 'About page'
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["MISSING_RATE_LIMITING"],
                expected_score=(2, 2),
                description="Flask public endpoint without rate limiting (LOW - doesn't reduce score)",
                tags=["python", "flask", "public", "low"]
            ),

            # ========== VULNERABLE - Express Authentication Endpoints ==========

            DetectorValidationSample(
                name="express_login_no_rate_limit",
                code='''
const express = require('express');
const app = express();

app.post('/login', (req, res) => {
    const { username, password } = req.body;
    // authenticate
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_RATE_LIMITING_AUTH"],
                expected_score=(0, 2),
                description="Express login endpoint without rate limiting (CRITICAL)",
                tags=["javascript", "express", "authentication", "critical"]
            ),

            DetectorValidationSample(
                name="express_password_reset_no_rate_limit",
                code='''
const express = require('express');
const app = express();

app.post('/password/reset', (req, res) => {
    const { email } = req.body;
    // send reset email
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_RATE_LIMITING_AUTH"],
                expected_score=(0, 2),
                description="Express password reset without rate limiting (CRITICAL)",
                tags=["javascript", "express", "authentication", "password"]
            ),

            # ========== SECURE - Express with Rate Limiting ==========

            DetectorValidationSample(
                name="express_login_with_rate_limit",
                code='''
const express = require('express');
const rateLimit = require('express-rate-limit');
const app = express();

const loginLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 5
});

app.post('/login', loginLimiter, (req, res) => {
    const { username, password } = req.body;
    // authenticate
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Express login endpoint with rate limiting",
                tags=["javascript", "express", "authentication", "secure"]
            ),

            # ========== VULNERABLE - Express Sensitive Endpoints ==========

            DetectorValidationSample(
                name="express_api_no_rate_limit",
                code='''
app.get('/api/users', (req, res) => {
    User.find({}, (err, users) => {
        res.json(users);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_RATE_LIMITING"],
                expected_score=(1, 2),
                description="Express API endpoint without rate limiting (MEDIUM)",
                tags=["javascript", "express", "sensitive", "api"]
            ),

            # ========== VULNERABLE - Express Public Endpoints ==========

            DetectorValidationSample(
                name="express_public_no_rate_limit",
                code='''
app.get('/about', (req, res) => {
    res.send('About page');
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["MISSING_RATE_LIMITING"],
                expected_score=(2, 2),
                description="Express public endpoint without rate limiting (LOW - doesn't reduce score)",
                tags=["javascript", "express", "public", "low"]
            ),

            # ========== VULNERABLE - Django REST Framework ==========

            DetectorValidationSample(
                name="django_apiview_no_throttle",
                code='''
from rest_framework.views import APIView
from rest_framework.response import Response

class UserListView(APIView):
    def get(self, request):
        users = User.objects.all()
        return Response(users)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_RATE_LIMITING"],
                expected_score=(1, 2),
                description="Django REST Framework APIView without throttle_classes (MEDIUM)",
                tags=["python", "django", "rest_framework", "apiview"]
            ),

            # ========== SECURE - Django REST Framework ==========

            DetectorValidationSample(
                name="django_apiview_with_throttle",
                code='''
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

class UserListView(APIView):
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        users = User.objects.all()
        return Response(users)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Django REST Framework APIView with throttle_classes",
                tags=["python", "django", "rest_framework", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="python_no_flask",
                code='''
def process_data(data):
    result = expensive_operation(data)
    return result
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Python code without Flask/Django (no web framework)",
                tags=["python", "edge_case", "no_framework"]
            ),

            DetectorValidationSample(
                name="javascript_no_express",
                code='''
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="JavaScript code without Express (no web framework)",
                tags=["javascript", "edge_case", "no_framework"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRateLimitingDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Rate Limiting detector validation tests PASSED")
        print("The RateLimitingDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Rate Limiting detector validation tests FAILED")
        print("The RateLimitingDetector has accuracy issues that must be fixed.")
        sys.exit(1)
