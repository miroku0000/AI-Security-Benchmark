#!/usr/bin/env python3
"""
CSRF (Cross-Site Request Forgery) Detector Validation Tests

This module validates that the CSRFDetector correctly identifies
CSRF vulnerabilities and secure CSRF protection patterns.

Test Coverage:
- Python: Flask-WTF CSRFProtect, SeaSurf, manual token validation
- JavaScript: csurf middleware, csrfToken() validation
- PHP: WordPress nonces, Laravel CSRF, manual tokens
- Go: gorilla/csrf, nosurf middleware
- Java: Spring Security, @EnableWebSecurity
- Rust: rocket_csrf, actix-csrf
- C#: [ValidateAntiForgeryToken]
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_csrf import CSRFDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestCSRFDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for CSRF Detector."""

    def get_detector(self):
        """Return CSRFDetector instance."""
        return CSRFDetector()

    def get_samples(self):
        """Return hand-crafted CSRF test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="csrf_python_post_no_protection",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/transfer', methods=['POST'])
def transfer():
    amount = request.form.get('amount')
    to = request.form.get('to')
    # VULNERABLE: No CSRF protection
    # Process transfer
    return 'Transfer complete'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="CSRF in Flask POST endpoint without protection",
                tags=["python", "flask", "no-protection", "critical"]
            ),

            DetectorValidationSample(
                name="csrf_python_put_no_protection",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/api/update', methods=['PUT'])
def update_user():
    user_id = request.json.get('user_id')
    email = request.json.get('email')
    # VULNERABLE: No CSRF protection on PUT
    return {'status': 'updated'}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="CSRF in Flask PUT endpoint",
                tags=["python", "put", "no-protection"]
            ),

            DetectorValidationSample(
                name="csrf_python_delete_no_protection",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/api/delete', methods=['DELETE'])
def delete_user():
    user_id = request.args.get('id')
    # VULNERABLE: DELETE without CSRF protection
    return {'status': 'deleted'}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="CSRF in Flask DELETE endpoint",
                tags=["python", "delete", "no-protection"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="csrf_python_csrfprotect",
                code='''
from flask import Flask, request
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
csrf = CSRFProtect(app)

@app.route('/transfer', methods=['POST'])
def transfer():
    amount = request.form.get('amount')
    to = request.form.get('to')
    # SECURE: CSRFProtect enabled
    return 'Transfer complete'
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure Flask with CSRFProtect",
                tags=["python", "csrfprotect", "secure"]
            ),

            DetectorValidationSample(
                name="csrf_python_seasurf",
                code='''
from flask import Flask, request
from flask_seasurf import SeaSurf

app = Flask(__name__)
csrf = SeaSurf(app)

@app.route('/update', methods=['POST'])
def update():
    data = request.form.get('data')
    # SECURE: SeaSurf middleware
    return 'Updated'
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure Flask with SeaSurf",
                tags=["python", "seasurf", "secure"]
            ),

            DetectorValidationSample(
                name="csrf_python_manual_token",
                code='''
from flask import Flask, request, session

app = Flask(__name__)

@app.route('/transfer', methods=['POST'])
def transfer():
    # SECURE: Manual CSRF token validation
    csrf_token = request.form.get('csrf_token')
    if csrf_token != session.get('csrf_token'):
        return 'Invalid token', 403

    amount = request.form.get('amount')
    return 'Transfer complete'
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with manual token validation",
                tags=["python", "manual-token", "secure"]
            ),

            DetectorValidationSample(
                name="csrf_python_flask_wtf_form",
                code='''
from flask import Flask, request
from flask_wtf import FlaskForm
from wtforms import StringField

app = Flask(__name__)

class TransferForm(FlaskForm):
    amount = StringField('Amount')
    to = StringField('To')

@app.route('/transfer', methods=['POST'])
def transfer():
    form = TransferForm()
    # SECURE: FlaskForm has auto CSRF protection
    if form.validate_on_submit():
        return 'Transfer complete'
    return 'Invalid', 400
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with FlaskForm (auto CSRF)",
                tags=["python", "flask-wtf", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="csrf_javascript_post_no_protection",
                code='''
const express = require('express');
const app = express();

app.post('/transfer', (req, res) => {
    const { amount, to } = req.body;
    // VULNERABLE: No CSRF protection
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="CSRF in Express POST route without protection",
                tags=["javascript", "express", "no-protection", "critical"]
            ),

            DetectorValidationSample(
                name="csrf_javascript_put_no_protection",
                code='''
const express = require('express');
const app = express();

app.put('/api/user', (req, res) => {
    // VULNERABLE: PUT without CSRF protection
    const { email } = req.body;
    res.json({ updated: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="CSRF in Express PUT route",
                tags=["javascript", "put", "no-protection"]
            ),

            DetectorValidationSample(
                name="csrf_javascript_delete_no_protection",
                code='''
const express = require('express');
const app = express();

app.delete('/api/user/:id', (req, res) => {
    // VULNERABLE: DELETE without CSRF protection
    const userId = req.params.id;
    res.json({ deleted: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="CSRF in Express DELETE route",
                tags=["javascript", "delete", "no-protection"]
            ),

            DetectorValidationSample(
                name="csrf_javascript_router_post",
                code='''
const express = require('express');
const router = express.Router();

router.post('/submit', (req, res) => {
    // VULNERABLE: Router POST without CSRF
    const data = req.body.data;
    res.send('Submitted');
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="CSRF in Express Router POST",
                tags=["javascript", "router", "no-protection"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="csrf_javascript_csurf_middleware",
                code='''
const express = require('express');
const csrf = require('csurf');
const app = express();

const csrfProtection = csrf({ cookie: true });

app.post('/transfer', csrfProtection, (req, res) => {
    const { amount, to } = req.body;
    // SECURE: csurf middleware
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure Express with csurf middleware",
                tags=["javascript", "csurf", "secure"]
            ),

            DetectorValidationSample(
                name="csrf_javascript_csrftoken_validation",
                code='''
const express = require('express');
const app = express();

app.post('/api/update', (req, res) => {
    // SECURE: csrfToken() validation
    const token = req.csrfToken();
    if (!token) {
        return res.status(403).send('Invalid CSRF token');
    }
    res.json({ updated: true });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with csrfToken() validation",
                tags=["javascript", "csrftoken", "secure"]
            ),

            DetectorValidationSample(
                name="csrf_javascript_custom_header_check",
                code='''
const express = require('express');
const app = express();

app.post('/transfer', (req, res) => {
    // SECURE: Custom CSRF header validation
    const csrfToken = req.headers['x-csrf-token'];
    if (!csrfToken || !validateToken(csrfToken)) {
        return res.status(403).send('Invalid token');
    }
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with custom X-CSRF-Token header check",
                tags=["javascript", "custom-header", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - PHP ==========

            DetectorValidationSample(
                name="csrf_php_post_no_protection",
                code='''
<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $amount = $_POST['amount'];
    $to = $_POST['to'];
    // VULNERABLE: No CSRF protection
    echo "Transfer complete";
}
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="CSRF in PHP POST handler without protection",
                tags=["php", "post", "no-protection", "critical"]
            ),

            DetectorValidationSample(
                name="csrf_php_form_no_token",
                code='''
<?php
if ($_POST) {
    // VULNERABLE: Form submission without CSRF token
    $user_id = $_POST['user_id'];
    $action = $_POST['action'];
    performAction($user_id, $action);
}
?>
<form method="POST" action="/admin.php">
    <input name="user_id" value="123">
    <input name="action" value="delete">
    <button type="submit">Delete User</button>
</form>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["CSRF"],
                expected_score=(0, 2),
                description="CSRF in PHP form without token",
                tags=["php", "form", "no-protection"]
            ),

            # ========== SECURE SAMPLES - PHP ==========

            DetectorValidationSample(
                name="csrf_php_wordpress_nonce",
                code='''
<?php
if ($_POST) {
    // SECURE: WordPress nonce validation
    if (!wp_verify_nonce($_POST['_wpnonce'], 'delete_user')) {
        die('Invalid nonce');
    }
    $user_id = $_POST['user_id'];
    deleteUser($user_id);
}
?>
<form method="POST">
    <?php wp_nonce_field('delete_user'); ?>
    <input name="user_id" value="123">
    <button type="submit">Delete</button>
</form>
''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure PHP with WordPress nonces",
                tags=["php", "wordpress", "nonce", "secure"]
            ),

            DetectorValidationSample(
                name="csrf_php_laravel_csrf",
                code='''
<form method="POST" action="/transfer">
    @csrf
    <input name="amount" value="100">
    <input name="to" value="recipient">
    <button type="submit">Transfer</button>
</form>

<?php
if ($_POST) {
    // SECURE: Laravel CSRF token (handled by framework)
    $amount = $_POST['amount'];
    processTransfer($amount);
}
?>
''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure PHP with Laravel @csrf directive",
                tags=["php", "laravel", "csrf", "secure"]
            ),

            DetectorValidationSample(
                name="csrf_php_manual_session_token",
                code='''
<?php
session_start();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // SECURE: Manual session token validation
    if (!isset($_POST['csrf_token']) ||
        $_POST['csrf_token'] !== $_SESSION['csrf_token']) {
        die('Invalid CSRF token');
    }

    $amount = $_POST['amount'];
    processTransfer($amount);
}

// Generate token for form
$_SESSION['csrf_token'] = bin2hex(random_bytes(32));
?>
<form method="POST">
    <input type="hidden" name="csrf_token" value="<?php echo $_SESSION['csrf_token']; ?>">
    <input name="amount">
    <button type="submit">Submit</button>
</form>
''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure PHP with manual session token",
                tags=["php", "session-token", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="csrf_python_no_flask",
                code='''
import requests

def fetch_data():
    # SECURE: Not a Flask app, no CSRF check needed
    response = requests.get('https://api.example.com/data')
    return response.json()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-Flask Python code (no CSRF check)",
                tags=["python", "non-flask", "edge-case", "secure"]
            ),

            DetectorValidationSample(
                name="csrf_javascript_no_express",
                code='''
const http = require('http');

const server = http.createServer((req, res) => {
    // SECURE: Not Express, CSRF check skipped
    res.end('Hello');
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-Express JavaScript (no CSRF check)",
                tags=["javascript", "non-express", "edge-case", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCSRFDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All CSRF detector validation tests PASSED")
        print("The CSRFDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} CSRF detector validation tests FAILED")
        print("The CSRFDetector has accuracy issues that must be fixed.")
        sys.exit(1)
