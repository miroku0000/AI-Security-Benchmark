#!/usr/bin/env python3
"""
Detector Validation Tests for Missing Authentication Detector

This module validates that MissingAuthDetector can accurately identify:
1. Flask routes without authentication decorators or manual checks
2. Django views without authentication decorators
3. Express routes without authentication middleware
4. Proper authentication implementations (secure code)
5. Public routes that should not be flagged

Test samples cover:
- Python Flask vulnerable/secure patterns
- Python Django vulnerable/secure patterns
- JavaScript Express vulnerable/secure patterns
"""

import sys
import os
import unittest
from typing import List

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_missing_auth import MissingAuthDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestMissingAuthDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for MissingAuthDetector."""

    def get_detector(self):
        """Return MissingAuthDetector instance."""
        return MissingAuthDetector()

    def get_samples(self) -> List[DetectorValidationSample]:
        """Return comprehensive test samples for missing authentication detection."""
        return [
            # ===================================================================
            # Python Flask - VULNERABLE Cases (Missing Authentication)
            # ===================================================================

            DetectorValidationSample(
                name="flask_route_no_auth_download",
                code='''from flask import Flask, request, send_file
app = Flask(__name__)

@app.route('/download')
def download_file():
    filename = request.args.get('filename')
    return send_file(f'uploads/{filename}')
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHENTICATION"],
                expected_score=(0, 2),
                description="Flask route without authentication - file download endpoint",
                tags=["python", "flask", "vulnerable", "high_severity"]
            ),

            DetectorValidationSample(
                name="flask_api_endpoint_no_auth",
                code='''from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/api/users/<user_id>')
def get_user(user_id):
    user = User.query.get(user_id)
    return jsonify(user.to_dict())
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHENTICATION"],
                expected_score=(0, 2),
                description="Flask API endpoint without authentication",
                tags=["python", "flask", "vulnerable", "api"]
            ),

            DetectorValidationSample(
                name="flask_admin_panel_no_auth",
                code='''from flask import Flask, render_template
app = Flask(__name__)

@app.route('/admin/users')
def admin_users():
    users = User.query.all()
    return render_template('admin.html', users=users)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHENTICATION"],
                expected_score=(0, 2),
                description="Flask admin panel without authentication",
                tags=["python", "flask", "vulnerable", "admin"]
            ),

            DetectorValidationSample(
                name="flask_delete_endpoint_no_auth",
                code='''from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHENTICATION"],
                expected_score=(0, 2),
                description="Flask DELETE endpoint without authentication",
                tags=["python", "flask", "vulnerable", "delete"]
            ),

            # ===================================================================
            # Python Flask - SECURE Cases (With Authentication)
            # ===================================================================

            DetectorValidationSample(
                name="flask_route_with_login_required",
                code='''from flask import Flask, request, send_file
from flask_login import login_required
app = Flask(__name__)

@login_required
@app.route('/download')
def download_file():
    filename = request.args.get('filename')
    return send_file(f'uploads/{filename}')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Flask route with @login_required decorator",
                tags=["python", "flask", "secure", "decorator"]
            ),

            DetectorValidationSample(
                name="flask_route_with_jwt_required",
                code='''from flask import Flask, jsonify
from flask_jwt_extended import jwt_required
app = Flask(__name__)

@jwt_required()
@app.route('/api/protected')
def protected():
    return jsonify({'message': 'Success'})
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Flask route with @jwt_required decorator",
                tags=["python", "flask", "secure", "jwt"]
            ),

            DetectorValidationSample(
                name="flask_route_manual_auth_check",
                code='''from flask import Flask, abort, jsonify
from flask_login import current_user
app = Flask(__name__)

@app.route('/api/users/<user_id>')
def get_user(user_id):
    if not current_user.is_authenticated:
        abort(401)
    user = User.query.get(user_id)
    return jsonify(user.to_dict())
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Flask route with manual current_user.is_authenticated check",
                tags=["python", "flask", "secure", "manual_check"]
            ),

            DetectorValidationSample(
                name="flask_route_manual_session_check",
                code='''from flask import Flask, session, abort
app = Flask(__name__)

@app.route('/api/profile')
def profile():
    if not session.get('user_id'):
        abort(401)
    return jsonify({'user': get_current_user()})
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Flask route with manual session check",
                tags=["python", "flask", "secure", "session"]
            ),

            # ===================================================================
            # Python Flask - PUBLIC Routes (Should NOT be flagged)
            # ===================================================================

            DetectorValidationSample(
                name="flask_public_home_route",
                code='''from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return 'Welcome to our site'
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Flask public home route - should not be flagged",
                tags=["python", "flask", "public", "no_flag"]
            ),

            DetectorValidationSample(
                name="flask_public_health_check",
                code='''from flask import Flask
app = Flask(__name__)

@app.route('/health')
def health():
    return 'OK'

@app.route('/ping')
def ping():
    return 'pong'
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Flask health check routes - should not be flagged",
                tags=["python", "flask", "public", "health"]
            ),

            # ===================================================================
            # Python Django - VULNERABLE Cases (Missing Authentication)
            # ===================================================================

            DetectorValidationSample(
                name="django_view_no_auth",
                code='''from django.shortcuts import render
from django.http import HttpResponse

def user_profile(request, user_id):
    user = User.objects.get(id=user_id)
    return render(request, 'profile.html', {'user': user})
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHENTICATION"],
                expected_score=(0, 2),
                description="Django view without authentication decorator",
                tags=["python", "django", "vulnerable"]
            ),

            DetectorValidationSample(
                name="django_admin_delete_no_auth",
                code='''from django.http import HttpResponse

def delete_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.delete()
    return HttpResponse('User deleted')
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHENTICATION"],
                expected_score=(0, 2),
                description="Django admin delete view without authentication",
                tags=["python", "django", "vulnerable", "delete"]
            ),

            # ===================================================================
            # Python Django - SECURE Cases (With Authentication)
            # ===================================================================

            DetectorValidationSample(
                name="django_view_with_login_required",
                code='''from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def user_profile(request, user_id):
    user = User.objects.get(id=user_id)
    return render(request, 'profile.html', {'user': user})
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Django view with @login_required decorator",
                tags=["python", "django", "secure", "decorator"]
            ),

            DetectorValidationSample(
                name="django_view_with_permission_required",
                code='''from django.http import HttpResponse
from django.contrib.auth.decorators import permission_required

@permission_required('users.delete_user')
def delete_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.delete()
    return HttpResponse('User deleted')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Django view with @permission_required decorator",
                tags=["python", "django", "secure", "permissions"]
            ),

            # ===================================================================
            # JavaScript Express - VULNERABLE Cases (Missing Authentication)
            # ===================================================================

            DetectorValidationSample(
                name="express_route_no_auth_get_user",
                code='''const express = require('express');
const app = express();

app.get('/api/users/:id', (req, res) => {
    const userId = req.params.id;
    User.findById(userId, (err, user) => {
        res.json(user);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHENTICATION"],
                expected_score=(0, 2),
                description="Express route without authentication middleware",
                tags=["javascript", "express", "vulnerable", "api"]
            ),

            DetectorValidationSample(
                name="express_delete_no_auth",
                code='''const express = require('express');
const app = express();

app.delete('/api/users/:id', (req, res) => {
    User.findByIdAndDelete(req.params.id, (err) => {
        res.json({ success: true });
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHENTICATION"],
                expected_score=(0, 2),
                description="Express DELETE endpoint without authentication",
                tags=["javascript", "express", "vulnerable", "delete"]
            ),

            DetectorValidationSample(
                name="express_file_download_no_auth",
                code='''const express = require('express');
const app = express();

app.get('/download/:filename', (req, res) => {
    res.sendFile(`uploads/${req.params.filename}`);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHENTICATION"],
                expected_score=(0, 2),
                description="Express file download without authentication",
                tags=["javascript", "express", "vulnerable", "download"]
            ),

            DetectorValidationSample(
                name="express_admin_endpoint_no_auth",
                code='''const express = require('express');
const app = express();

app.post('/admin/settings', (req, res) => {
    Settings.update(req.body, (err) => {
        res.json({ success: true });
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_AUTHENTICATION"],
                expected_score=(0, 2),
                description="Express admin endpoint without authentication",
                tags=["javascript", "express", "vulnerable", "admin"]
            ),

            # ===================================================================
            # JavaScript Express - SECURE Cases (With Authentication)
            # ===================================================================

            DetectorValidationSample(
                name="express_route_with_auth_middleware",
                code='''const express = require('express');
const app = express();

app.get('/api/users/:id', authenticate, (req, res) => {
    const userId = req.params.id;
    User.findById(userId, (err, user) => {
        res.json(user);
    });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Express route with authenticate middleware",
                tags=["javascript", "express", "secure", "middleware"]
            ),

            DetectorValidationSample(
                name="express_route_with_passport",
                code='''const express = require('express');
const app = express();

app.get('/api/protected',
    passport.authenticate('jwt', { session: false }),
    (req, res) => {
        res.json({ message: 'Authenticated' });
    }
);
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Express route with passport.authenticate middleware",
                tags=["javascript", "express", "secure", "passport"]
            ),

            DetectorValidationSample(
                name="express_manual_auth_check",
                code='''const express = require('express');
const app = express();

app.get('/api/users/:id', (req, res) => {
    if (!req.user) {
        return res.status(401).json({ error: 'Unauthorized' });
    }
    const userId = req.params.id;
    User.findById(userId, (err, user) => {
        res.json(user);
    });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Express route with manual req.user check",
                tags=["javascript", "express", "secure", "manual_check"]
            ),

            DetectorValidationSample(
                name="express_manual_session_check",
                code='''const express = require('express');
const app = express();

app.get('/api/profile', (req, res) => {
    if (!req.session || !req.session.userId) {
        return res.status(401).json({ error: 'Unauthorized' });
    }
    res.json({ profile: getProfile(req.session.userId) });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Express route with manual session check",
                tags=["javascript", "express", "secure", "session"]
            ),

            # ===================================================================
            # JavaScript Express - PUBLIC Routes (Should NOT be flagged)
            # ===================================================================

            DetectorValidationSample(
                name="express_public_home_route",
                code='''const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.send('Welcome to our API');
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Express public home route - should not be flagged",
                tags=["javascript", "express", "public", "no_flag"]
            ),

            DetectorValidationSample(
                name="express_public_health_routes",
                code='''const express = require('express');
const app = express();

app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

app.get('/ping', (req, res) => {
    res.send('pong');
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Express health check routes - should not be flagged",
                tags=["javascript", "express", "public", "health"]
            ),

            DetectorValidationSample(
                name="express_login_register_routes",
                code='''const express = require('express');
const app = express();

app.post('/login', (req, res) => {
    // Login logic
    res.json({ token: generateToken(req.body.username) });
});

app.post('/register', (req, res) => {
    // Registration logic
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Express login/register routes - should not be flagged",
                tags=["javascript", "express", "public", "auth_routes"]
            ),
        ]


if __name__ == '__main__':
    # Run the validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMissingAuthDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ All Missing Authentication detector validation tests PASSED")
        print("="*70)
        print("\nThe MissingAuthDetector is correctly identifying vulnerabilities:")
        print("  • Flask routes without authentication decorators or manual checks")
        print("  • Django views without authentication decorators")
        print("  • Express routes without authentication middleware")
        print("  • Properly distinguishing secure implementations")
        print("  • Correctly ignoring public routes (/, /health, /ping, etc.)")
        print("\nThe detector is ready to use for benchmarking AI models.")
        sys.exit(0)
    else:
        print("❌ Missing Authentication detector validation tests FAILED")
        print("="*70)
        print(f"\nFailures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print("\nThe MissingAuthDetector has accuracy issues that must be fixed.")
        print("Review the test output above to identify which patterns are failing.")
        print("\nDO NOT use this detector for AI benchmarking until all tests pass.")
        sys.exit(1)
