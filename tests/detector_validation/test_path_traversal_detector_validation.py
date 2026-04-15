#!/usr/bin/env python3
"""
Path Traversal Detector Validation Tests

This module validates that the PathTraversalDetector correctly identifies
path traversal vulnerabilities and secure path handling patterns.

Test Coverage:
- Python: os.path.join, string concatenation, os.path.basename
- JavaScript: path.join, string concatenation, path.basename
- File operations: open(), send_file(), fs.readFile()
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_path_traversal import PathTraversalDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPathTraversalDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Path Traversal Detector."""

    def get_detector(self):
        """Return PathTraversalDetector instance."""
        return PathTraversalDetector()

    def get_samples(self):
        """Return hand-crafted path traversal test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="path_python_string_concat",
                code='''
from flask import Flask, request, send_file

app = Flask(__name__)

@app.route('/download')
def download_file():
    filename = request.args.get('file', '')
    # VULNERABLE: String concatenation with user input
    filepath = './uploads/' + filename
    return send_file(filepath)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="Path traversal via string concatenation",
                tags=["python", "concatenation", "basic"]
            ),

            DetectorValidationSample(
                name="path_python_fstring",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/read')
def read_file():
    filename = request.args.get('file', 'default.txt')
    # VULNERABLE: f-string with user input
    with open(f'./data/{filename}', 'r') as f:
        return f.read()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="Path traversal via f-string",
                tags=["python", "f-string", "basic"]
            ),

            DetectorValidationSample(
                name="path_python_format_method",
                code='''
import os

def delete_user_file(filename):
    # VULNERABLE: .format() method with user input
    filepath = './uploads/{}'.format(filename)
    os.remove(filepath)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="Path traversal via .format() method",
                tags=["python", "format", "basic"]
            ),

            DetectorValidationSample(
                name="path_python_os_path_join",
                code='''
import os
from flask import Flask, request

app = Flask(__name__)

@app.route('/file')
def get_file():
    filename = request.args.get('name', '')
    # VULNERABLE: os.path.join with user input (no validation)
    filepath = os.path.join('./uploads', filename)
    with open(filepath, 'r') as f:
        return f.read()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="Path traversal via os.path.join without validation",
                tags=["python", "os.path.join", "basic"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="path_python_basename",
                code='''
import os
from flask import Flask, request, send_file

app = Flask(__name__)

@app.route('/download')
def download_file():
    filename = request.args.get('file', '')
    # SECURE: os.path.basename() strips directory traversal
    safe_filename = os.path.basename(filename)
    filepath = os.path.join('./uploads', safe_filename)
    return send_file(filepath)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure path handling with os.path.basename()",
                tags=["python", "basename", "secure"]
            ),

            DetectorValidationSample(
                name="path_python_allowlist",
                code='''
from flask import Flask, request

app = Flask(__name__)

ALLOWED_FILES = ['data.txt', 'report.pdf', 'image.jpg']

@app.route('/download')
def download_file():
    filename = request.args.get('file', '')
    # SECURE: Allowlist validation
    if filename not in ALLOWED_FILES:
        return "File not allowed", 403
    filepath = './uploads/' + filename
    return send_file(filepath)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with allowlist validation",
                tags=["python", "allowlist", "secure"]
            ),

            DetectorValidationSample(
                name="path_python_hardcoded",
                code='''
from flask import Flask, send_file

app = Flask(__name__)

@app.route('/logo')
def get_logo():
    # SECURE: Hardcoded path, no user input
    return send_file('./static/logo.png')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure hardcoded path",
                tags=["python", "hardcoded", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="path_javascript_concat",
                code='''
const express = require('express');
const fs = require('fs');
const app = express();

app.get('/read', (req, res) => {
    const filename = req.query.file;
    // VULNERABLE: String concatenation with user input
    const filepath = './uploads/' + filename;
    fs.readFile(filepath, 'utf8', (err, data) => {
        if (err) throw err;
        res.send(data);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="Path traversal via string concatenation in JavaScript",
                tags=["javascript", "concatenation", "basic"]
            ),

            DetectorValidationSample(
                name="path_javascript_template_literal",
                code='''
const express = require('express');
const fs = require('fs');

app.get('/download', (req, res) => {
    const file = req.query.filename;
    // VULNERABLE: Template literal with user input
    const path = `./data/${file}`;
    res.sendFile(path);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="Path traversal via template literal",
                tags=["javascript", "template-literal", "basic"]
            ),

            DetectorValidationSample(
                name="path_javascript_path_join",
                code='''
const express = require('express');
const path = require('path');
const fs = require('fs');

app.get('/file', (req, res) => {
    const filename = req.query.name;
    // VULNERABLE: path.join with user input (no validation)
    const filepath = path.join('./uploads', filename);
    fs.readFile(filepath, 'utf8', (err, data) => {
        res.send(data);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="Path traversal via path.join without validation",
                tags=["javascript", "path.join", "basic"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="path_javascript_basename",
                code='''
const express = require('express');
const path = require('path');
const fs = require('fs');

app.get('/download', (req, res) => {
    const filename = req.query.file;
    // SECURE: path.basename() strips directory traversal
    const safeName = path.basename(filename);
    const filepath = path.join('./uploads', safeName);
    res.sendFile(filepath);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure path handling with path.basename()",
                tags=["javascript", "basename", "secure"]
            ),

            DetectorValidationSample(
                name="path_javascript_regex_validation",
                code='''
const express = require('express');

app.get('/file', (req, res) => {
    const filename = req.query.name;
    // SECURE: Regex validation for safe filenames
    if (!/^[a-zA-Z0-9_-]+\\.txt$/.test(filename)) {
        return res.status(400).send('Invalid filename');
    }
    const filepath = './data/' + filename;
    res.sendFile(filepath);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with regex validation",
                tags=["javascript", "regex", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="path_python_realpath_check",
                code='''
import os
from flask import Flask, request

app = Flask(__name__)

@app.route('/read')
def read_file():
    filename = request.args.get('file', '')
    base_dir = os.path.realpath('./uploads')
    filepath = os.path.realpath(os.path.join(base_dir, filename))

    # SECURE: Verify file is within base directory
    if not filepath.startswith(base_dir):
        return "Access denied", 403

    with open(filepath, 'r') as f:
        return f.read()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with realpath validation",
                tags=["python", "realpath", "edge-case", "secure"]
            ),

            DetectorValidationSample(
                name="path_python_multiple_params",
                code='''
from flask import Flask, request

app = Flask(__name__)

@app.route('/download')
def download():
    folder = request.args.get('folder', '')
    filename = request.args.get('file', '')
    # VULNERABLE: Multiple user inputs in path
    filepath = f'./data/{folder}/{filename}'
    return send_file(filepath)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["PATH_TRAVERSAL"],
                expected_score=(0, 2),
                description="Path traversal with multiple user inputs",
                tags=["python", "multiple-inputs", "edge-case"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPathTraversalDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Path Traversal detector validation tests PASSED")
        print("The PathTraversalDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Path Traversal detector validation tests FAILED")
        print("The PathTraversalDetector has accuracy issues that must be fixed.")
        sys.exit(1)
