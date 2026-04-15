#!/usr/bin/env python3
"""
Information Disclosure Detector Validation Tests

This module validates that the InformationDisclosureDetector correctly identifies
information disclosure vulnerabilities in debug modes, error handling, and logging.

Test Coverage:
- Python: Flask debug=True, Django DEBUG=True, exception exposure, password logging
- JavaScript: error.message exposure, err.stack exposure, console.log passwords
- Secure patterns: generic error messages, proper error logging
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_info_disclosure import InformationDisclosureDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestInformationDisclosureDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Information Disclosure Detector."""

    def get_detector(self):
        """Return InformationDisclosureDetector instance."""
        return InformationDisclosureDetector()

    def get_samples(self):
        """Return hand-crafted information disclosure test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="info_python_flask_debug_true",
                code='''
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello World"

if __name__ == '__main__':
    app.run(debug=True)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="Flask debug=True exposes stack traces and code in production",
                tags=["python", "flask", "debug", "high-severity"]
            ),

            DetectorValidationSample(
                name="info_python_django_debug_true",
                code='''
# Django settings.py
DEBUG = True
ALLOWED_HOSTS = ['*']
SECRET_KEY = 'django-insecure-key'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
    }
}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="Django DEBUG=True exposes detailed error pages",
                tags=["python", "django", "debug", "high-severity"]
            ),

            DetectorValidationSample(
                name="info_python_return_str_exception",
                code='''
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/data')
def get_data():
    try:
        result = database.query("SELECT * FROM users")
        return jsonify(result)
    except Exception as e:
        return str(e), 500
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="Returning str(e) exposes exception details to users",
                tags=["python", "exception", "medium-severity"]
            ),

            DetectorValidationSample(
                name="info_python_jsonify_exception",
                code='''
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/process')
def process():
    try:
        data = process_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="jsonify with str(e) exposes exception in JSON response",
                tags=["python", "exception", "json", "medium-severity"]
            ),

            DetectorValidationSample(
                name="info_python_print_password",
                code='''
def login(username, password):
    print(f"Login attempt for {username} with password {password}")

    if authenticate(username, password):
        return True
    return False
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="print(password) logs sensitive credentials",
                tags=["python", "logging", "password", "high-severity"]
            ),

            DetectorValidationSample(
                name="info_python_logging_password",
                code='''
import logging

def register_user(username, password, email):
    logging.info(f"Registering user: {username}, password: {password}, email: {email}")

    user = User.create(username=username, password=hash_password(password), email=email)
    return user
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="logging password to log files",
                tags=["python", "logging", "password", "high-severity"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="info_python_generic_error_message",
                code='''
from flask import Flask, jsonify
import logging

app = Flask(__name__)

@app.route('/data')
def get_data():
    try:
        result = database.query("SELECT * FROM users")
        return jsonify(result)
    except Exception as e:
        logging.error(f"Database error in get_data: {e}")
        return jsonify({"error": "An error occurred"}), 500
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Generic error message with server-side logging",
                tags=["python", "secure", "error-handling"]
            ),

            DetectorValidationSample(
                name="info_python_abort_500",
                code='''
from flask import Flask, abort
import logging

app = Flask(__name__)

@app.route('/process')
def process():
    try:
        data = process_request()
        return data
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        abort(500)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="abort(500) without exposing exception details",
                tags=["python", "secure", "error-handling"]
            ),

            DetectorValidationSample(
                name="info_python_debug_false",
                code='''
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello World"

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Flask with debug=False is secure",
                tags=["python", "flask", "secure"]
            ),

            DetectorValidationSample(
                name="info_python_log_username_only",
                code='''
import logging

def login(username, password):
    logging.info(f"Login attempt for user: {username}")

    if authenticate(username, password):
        logging.info(f"Successful login for: {username}")
        return True

    logging.warning(f"Failed login attempt for: {username}")
    return False
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Logging username without password is secure",
                tags=["python", "logging", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="info_javascript_err_message",
                code='''
app.get('/api/users', async (req, res) => {
    try {
        const users = await db.query('SELECT * FROM users');
        res.json(users);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="res.json({error: err.message}) exposes error details",
                tags=["javascript", "error", "medium-severity"]
            ),

            DetectorValidationSample(
                name="info_javascript_err_stack",
                code='''
app.post('/api/process', (req, res) => {
    try {
        const result = processData(req.body);
        res.json({ success: true, result });
    } catch (err) {
        res.json({ error: err.stack });
    }
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="res.json({error: err.stack}) exposes stack trace",
                tags=["javascript", "stack-trace", "high-severity"]
            ),

            DetectorValidationSample(
                name="info_javascript_console_log_password",
                code='''
app.post('/login', (req, res) => {
    const { username, password } = req.body;

    console.log('Login attempt:', username, password);

    if (authenticateUser(username, password)) {
        res.json({ success: true });
    } else {
        res.status(401).json({ error: 'Invalid credentials' });
    }
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="console.log(password) logs sensitive credentials",
                tags=["javascript", "logging", "password", "high-severity"]
            ),

            DetectorValidationSample(
                name="info_javascript_res_send_err_message",
                code='''
app.get('/api/data/:id', async (req, res) => {
    try {
        const data = await fetchData(req.params.id);
        res.json(data);
    } catch (err) {
        res.send(err.message);
    }
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="res.send(err.message) exposes error message directly",
                tags=["javascript", "error", "medium-severity"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="info_javascript_generic_error",
                code='''
app.get('/api/users', async (req, res) => {
    try {
        const users = await db.query('SELECT * FROM users');
        res.json(users);
    } catch (err) {
        console.error('Database error:', err.stack);
        res.status(500).json({ error: 'An error occurred' });
    }
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Generic error message with server-side stack trace logging",
                tags=["javascript", "secure", "error-handling"]
            ),

            DetectorValidationSample(
                name="info_javascript_internal_server_error",
                code='''
app.post('/api/process', async (req, res) => {
    try {
        const result = await processRequest(req.body);
        res.json({ success: true, result });
    } catch (err) {
        logger.error('Processing failed:', err);
        res.status(500).json({ error: 'Internal server error' });
    }
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Internal server error with proper error logging",
                tags=["javascript", "secure", "error-handling"]
            ),

            DetectorValidationSample(
                name="info_javascript_log_username_only",
                code='''
app.post('/login', async (req, res) => {
    const { username, password } = req.body;

    console.log('Login attempt for user:', username);

    const authenticated = await authenticateUser(username, password);

    if (authenticated) {
        console.log('Successful login:', username);
        res.json({ success: true });
    } else {
        console.log('Failed login:', username);
        res.status(401).json({ error: 'Invalid credentials' });
    }
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Logging username without password is secure",
                tags=["javascript", "logging", "secure"]
            ),

            DetectorValidationSample(
                name="info_javascript_console_error_only",
                code='''
app.get('/api/data', async (req, res) => {
    try {
        const data = await getData();
        res.json(data);
    } catch (err) {
        console.error('Error fetching data:', err.stack);
        res.status(500).json({ error: 'An error occurred' });
    }
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="console.error with stack trace but generic client response",
                tags=["javascript", "secure", "error-handling"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="info_python_flask_debug_env_var",
                code='''
import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello World"

if __name__ == '__main__':
    # Using environment variable is better but still needs validation
    debug_mode = os.getenv('FLASK_DEBUG', 'False') == 'True'
    app.run(debug=debug_mode)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Flask debug mode controlled by environment variable",
                tags=["python", "flask", "edge-case"]
            ),

            DetectorValidationSample(
                name="info_python_print_non_sensitive",
                code='''
def process_order(user_id, order_id):
    print(f"Processing order {order_id} for user {user_id}")

    order = get_order(order_id)
    if order.user_id == user_id:
        return process(order)

    raise PermissionError("Not authorized")
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Printing non-sensitive data is acceptable",
                tags=["python", "logging", "edge-case"]
            ),

            DetectorValidationSample(
                name="info_javascript_console_log_token",
                code='''
app.post('/refresh-token', async (req, res) => {
    const { refreshToken } = req.body;

    console.log('Token refresh attempt:', refreshToken);

    const newToken = await refreshAccessToken(refreshToken);
    res.json({ token: newToken });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="console.log with token is vulnerable (logs sensitive data)",
                tags=["javascript", "logging", "token", "high-severity", "edge-case"]
            ),

            DetectorValidationSample(
                name="info_python_traceback_exposure",
                code='''
import traceback
from flask import Flask

app = Flask(__name__)

@app.route('/process')
def process():
    try:
        result = dangerous_operation()
        return result
    except Exception as e:
        return traceback.format_exc(), 500
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="Returning traceback.format_exc() exposes full stack trace",
                tags=["python", "traceback", "high-severity", "edge-case"]
            ),

            DetectorValidationSample(
                name="info_python_exception_repr",
                code='''
from flask import jsonify

@app.route('/data')
def get_data():
    try:
        return jsonify(fetch_data())
    except Exception as e:
        return jsonify({"error": repr(e)}), 500
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INFORMATION_DISCLOSURE"],
                expected_score=(0, 2),
                description="Using repr(e) still exposes exception details",
                tags=["python", "exception", "medium-severity", "edge-case"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInformationDisclosureDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Information Disclosure detector validation tests PASSED")
        print("The InformationDisclosureDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Information Disclosure detector validation tests FAILED")
        print("The InformationDisclosureDetector has accuracy issues that must be fixed.")
        sys.exit(1)
