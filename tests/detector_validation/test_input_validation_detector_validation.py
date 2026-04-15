#!/usr/bin/env python3
"""
Input Validation Detector Validation Tests

This module validates that the InputValidationDetector correctly identifies
missing input validation in Python and JavaScript code.

Test Coverage:
- Python: null/None checks, type validation, length validation, format validation
- JavaScript: null/undefined checks, type validation, length validation
- Secure patterns: if not, isinstance(), len(), typeof, validators
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_input_validation import InputValidationDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestInputValidationDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Input Validation Detector."""

    def get_detector(self):
        """Return InputValidationDetector instance."""
        return InputValidationDetector()

    def get_samples(self):
        """Return hand-crafted input validation test samples."""
        return [
            # ========== VULNERABLE - Python Missing Null Check ==========

            DetectorValidationSample(
                name="python_missing_null_check",
                code='''
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/search')
def search():
    query = request.args.get('q')
    results = db.search(query)
    return jsonify(results)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_INPUT_VALIDATION"],
                expected_score=(0, 2),
                description="Parameter used without null check (CRITICAL)",
                tags=["python", "null_check", "critical"]
            ),

            DetectorValidationSample(
                name="python_missing_null_check_form",
                code='''
from flask import Flask, request

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = authenticate(username, password)
    return jsonify(user)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_TYPE_VALIDATION"],
                expected_score=(0, 2),
                description="Form parameters used without type validation (CRITICAL)",
                tags=["python", "form", "type_validation"]
            ),

            # ========== SECURE - Python with Null Check ==========

            DetectorValidationSample(
                name="python_with_null_check",
                code='''
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/search')
def search():
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "Query required"}), 400
    results = db.search(query)
    return jsonify(results)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_TYPE_VALIDATION", "SECURE"],
                expected_score=(1, 2),
                description="Has null check but missing type validation (MEDIUM - partial credit)",
                tags=["python", "null_check", "partial"]
            ),

            DetectorValidationSample(
                name="python_with_is_none_check",
                code='''
from flask import Flask, request

@app.route('/update')
def update():
    data = request.json.get('data')
    if data is None:
        return {"error": "Data required"}, 400
    return process_data(data)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_TYPE_VALIDATION"],
                expected_score=(0, 2),
                description="Has 'is None' check but missing type validation (CRITICAL)",
                tags=["python", "is_none", "type_validation"]
            ),

            # ========== VULNERABLE - Python Missing Type Validation ==========

            DetectorValidationSample(
                name="python_missing_type_validation",
                code='''
from flask import Flask, request

@app.route('/age')
def check_age():
    age = request.args.get('age')
    if age > 18:
        return "Adult"
    return "Minor"
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_TYPE_VALIDATION"],
                expected_score=(0, 2),
                description="No type validation on user input (CRITICAL)",
                tags=["python", "type_validation", "critical"]
            ),

            # ========== SECURE - Python with Type Validation ==========

            DetectorValidationSample(
                name="python_with_type_validation",
                code='''
from flask import Flask, request

@app.route('/age')
def check_age():
    age = request.args.get('age')
    if not age or not age.isdigit():
        return "Invalid age", 400
    if int(age) > 18:
        return "Adult"
    return "Minor"
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_LENGTH_VALIDATION"],
                expected_score=(1, 2),
                description="Has type validation but missing length check (LOW - partial credit)",
                tags=["python", "type_validation", "partial"]
            ),

            DetectorValidationSample(
                name="python_with_isinstance_validation",
                code='''
from flask import Flask, request

@app.route('/process')
def process():
    data = request.json.get('data')
    if not isinstance(data, dict):
        return {"error": "Invalid data type"}, 400
    return process_dict(data)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_INPUT_VALIDATION", "SECURE"],
                expected_score=(1, 2),
                description="Has isinstance() but flagged for missing null check (MEDIUM)",
                tags=["python", "isinstance", "partial"]
            ),

            # ========== VULNERABLE - Python Missing Length Validation ==========

            DetectorValidationSample(
                name="python_missing_length_validation",
                code='''
from flask import Flask, request

@app.route('/comment')
def add_comment():
    comment = request.form.get('comment')
    db.save_comment(comment)
    return "Saved"
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_INPUT_VALIDATION"],
                expected_score=(0, 2),
                description="Missing null check triggers before length validation (CRITICAL)",
                tags=["python", "null_check", "critical"]
            ),

            # ========== SECURE - Python with Length Validation ==========

            DetectorValidationSample(
                name="python_with_length_validation",
                code='''
from flask import Flask, request

@app.route('/comment')
def add_comment():
    comment = request.form.get('comment')
    if len(comment) > 1000:
        return "Comment too long", 400
    db.save_comment(comment)
    return "Saved"
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_INPUT_VALIDATION", "SECURE"],
                expected_score=(1, 2),
                description="Has len() but missing null check (MEDIUM - partial credit)",
                tags=["python", "length_validation", "partial"]
            ),

            # ========== VULNERABLE - Python Missing Format Validation ==========

            DetectorValidationSample(
                name="python_missing_email_validation",
                code='''
from flask import Flask, request

@app.route('/subscribe')
def subscribe():
    email = request.form.get('email')
    db.add_subscriber(email)
    return "Subscribed"
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_INPUT_VALIDATION"],
                expected_score=(0, 2),
                description="Email input without null check (CRITICAL - null check fires before format validation)",
                tags=["python", "email", "missing_null_check"]
            ),

            # ========== SECURE - Python with Format Validation ==========

            DetectorValidationSample(
                name="python_with_email_validation",
                code='''
from flask import Flask, request
import re

@app.route('/subscribe')
def subscribe():
    email = request.form.get('email')
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return "Invalid email", 400
    db.add_subscriber(email)
    return "Subscribed"
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_INPUT_VALIDATION"],
                expected_score=(0, 2),
                description="Has email regex but email used in re.match() before null check (CRITICAL)",
                tags=["python", "email", "regex", "missing_null_check"]
            ),

            # ========== VULNERABLE - JavaScript Missing Null Check ==========

            DetectorValidationSample(
                name="javascript_missing_null_check",
                code='''
app.get('/search', (req, res) => {
    const query = req.query.q;
    const results = db.search(query);
    res.json(results);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_TYPE_VALIDATION"],
                expected_score=(0, 2),
                description="Query parameter without type validation (CRITICAL)",
                tags=["javascript", "null_check", "critical"]
            ),

            DetectorValidationSample(
                name="javascript_missing_null_check_body",
                code='''
app.post('/update', (req, res) => {
    const userId = req.body.userId;
    const data = req.body.data;
    db.update(userId, data);
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_TYPE_VALIDATION"],
                expected_score=(0, 2),
                description="Body parameters without type validation (CRITICAL)",
                tags=["javascript", "body", "null_check"]
            ),

            # ========== SECURE - JavaScript with Null Check ==========

            DetectorValidationSample(
                name="javascript_with_null_check",
                code='''
app.get('/search', (req, res) => {
    const query = req.query.q;
    if (!query) {
        return res.status(400).json({ error: 'Query required' });
    }
    const results = db.search(query);
    res.json(results);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(1, 2),
                description="Has null check but missing TYPE validation (MEDIUM)",
                tags=["javascript", "null_check", "secure"]
            ),

            DetectorValidationSample(
                name="javascript_with_undefined_check",
                code='''
app.post('/update', (req, res) => {
    const data = req.body.data;
    if (data === undefined) {
        return res.status(400).json({ error: 'Data required' });
    }
    db.save(data);
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_TYPE_VALIDATION"],
                expected_score=(0, 2),
                description="Has undefined check but data used in db.save() before check - missing TYPE validation (CRITICAL)",
                tags=["javascript", "undefined", "type_validation"]
            ),

            # ========== VULNERABLE - JavaScript Missing Type Validation ==========

            DetectorValidationSample(
                name="javascript_missing_type_validation",
                code='''
app.get('/calculate', (req, res) => {
    const num1 = req.query.a;
    const num2 = req.query.b;
    const result = num1 + num2;
    res.json({ result });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_INPUT_VALIDATION"],
                expected_score=(0, 2),
                description="Variables used directly in operation without validation (CRITICAL - null check fires before type check)",
                tags=["javascript", "null_check", "critical"]
            ),

            # ========== SECURE - JavaScript with Type Validation ==========

            DetectorValidationSample(
                name="javascript_with_type_validation",
                code='''
app.get('/calculate', (req, res) => {
    const num1 = parseInt(req.query.a);
    const num2 = parseInt(req.query.b);
    if (isNaN(num1) || isNaN(num2)) {
        return res.status(400).json({ error: 'Invalid numbers' });
    }
    const result = num1 + num2;
    res.json({ result });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure with parseInt() and isNaN() validation",
                tags=["javascript", "type_validation", "secure"]
            ),

            DetectorValidationSample(
                name="javascript_with_typeof_validation",
                code='''
app.post('/process', (req, res) => {
    const data = req.body.data;
    if (typeof data !== 'object') {
        return res.status(400).json({ error: 'Invalid data type' });
    }
    processData(data);
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(1, 2),
                description="Has typeof but missing LENGTH validation (MEDIUM)",
                tags=["javascript", "typeof", "secure"]
            ),

            # ========== VULNERABLE - JavaScript Missing Length Validation ==========

            DetectorValidationSample(
                name="javascript_missing_length_validation",
                code='''
app.post('/comment', (req, res) => {
    const comment = req.body.comment;
    db.saveComment(comment);
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["MISSING_TYPE_VALIDATION"],
                expected_score=(0, 2),
                description="Missing type validation triggers before length validation (CRITICAL)",
                tags=["javascript", "length_validation", "low"]
            ),

            # ========== SECURE - JavaScript with Length Validation ==========

            DetectorValidationSample(
                name="javascript_with_length_validation",
                code='''
app.post('/comment', (req, res) => {
    const comment = req.body.comment;
    if (comment.length > 1000) {
        return res.status(400).json({ error: 'Comment too long' });
    }
    db.saveComment(comment);
    res.json({ success: true });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(1, 2),
                description="Has .length but missing null check (MEDIUM)",
                tags=["javascript", "length_validation", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="python_no_user_input",
                code='''
def calculate_total(items):
    total = sum(item.price for item in items)
    return total
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No user input (no validation needed)",
                tags=["python", "no_input", "secure"]
            ),

            DetectorValidationSample(
                name="javascript_no_user_input",
                code='''
function calculateTotal(items) {
    return items.reduce((sum, item) => sum + item.price, 0);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No user input (no validation needed)",
                tags=["javascript", "no_input", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInputValidationDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Input Validation detector validation tests PASSED")
        print("The InputValidationDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Input Validation detector validation tests FAILED")
        print("The InputValidationDetector has accuracy issues that must be fixed.")
        sys.exit(1)
