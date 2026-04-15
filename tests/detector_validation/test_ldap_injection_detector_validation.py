#!/usr/bin/env python3
"""
LDAP Injection Detector Validation Tests

This module validates that the LDAPInjectionDetector correctly identifies
LDAP injection vulnerabilities and secure LDAP query patterns.

Test Coverage:
- Python: f-strings, .format(), string concatenation, escape_filter_chars()
- JavaScript: template literals, string concatenation, ldap-escape library
- Secure patterns: escape_filter_chars(), ldap-escape, proper escaping
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_ldap_injection import LDAPInjectionDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestLDAPInjectionDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for LDAP Injection Detector."""

    def get_detector(self):
        """Return LDAPInjectionDetector instance."""
        return LDAPInjectionDetector()

    def get_samples(self):
        """Return hand-crafted LDAP injection test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="ldap_python_fstring_injection",
                code='''
import ldap

def search_user(username):
    conn = ldap.initialize('ldap://localhost:389')
    # VULNERABLE: f-string allows LDAP injection
    filter_str = f"(uid={username})"
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LDAP_INJECTION"],
                expected_score=(0, 2),
                description="LDAP injection via f-string",
                tags=["python", "f-string", "critical"]
            ),

            DetectorValidationSample(
                name="ldap_python_string_concatenation",
                code='''
import ldap

def authenticate(username, password):
    conn = ldap.initialize('ldap://localhost:389')
    # VULNERABLE: String concatenation in filter
    filter_str = "(uid=" + username + ")"
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LDAP_INJECTION"],
                expected_score=(0, 2),
                description="LDAP injection via string concatenation",
                tags=["python", "string-concat", "critical"]
            ),

            DetectorValidationSample(
                name="ldap_python_format_method",
                code='''
import ldap

def find_user(email):
    conn = ldap.initialize('ldap://localhost:389')
    # VULNERABLE: .format() method allows injection
    filter_str = "(mail={})".format(email)
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LDAP_INJECTION"],
                expected_score=(0, 2),
                description="LDAP injection via .format() method",
                tags=["python", "format", "basic"]
            ),

            DetectorValidationSample(
                name="ldap_python_percent_formatting",
                code='''
import ldap

def search_by_cn(common_name):
    conn = ldap.initialize('ldap://localhost:389')
    # VULNERABLE: % formatting in filter
    filter_str = "(cn=%s)" % common_name
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LDAP_INJECTION"],
                expected_score=(0, 2),
                description="LDAP injection via % formatting",
                tags=["python", "percent-format", "basic"]
            ),

            DetectorValidationSample(
                name="ldap_python_user_input_no_escaping",
                code='''
import ldap
import sys

def search_user():
    username = sys.argv[1]
    conn = ldap.initialize('ldap://localhost:389')
    # VULNERABLE: User input without escaping
    filter_str = f"(uid={username})"
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LDAP_INJECTION"],
                expected_score=(0, 2),
                description="LDAP injection with sys.argv input",
                tags=["python", "user-input", "critical"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="ldap_python_escape_filter_chars",
                code='''
import ldap
from ldap3.utils.conv import escape_filter_chars

def search_user(username):
    conn = ldap.initialize('ldap://localhost:389')
    # SECURE: escape_filter_chars() escapes special characters
    safe_username = escape_filter_chars(username)
    filter_str = f"(uid={safe_username})"
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with escape_filter_chars()",
                tags=["python", "escape-filter-chars", "secure"]
            ),

            DetectorValidationSample(
                name="ldap_python_imported_escape",
                code='''
from ldap3.utils.conv import escape_filter_chars
import ldap

def authenticate(username, password):
    conn = ldap.initialize('ldap://localhost:389')
    # SECURE: Escaped username
    safe_user = escape_filter_chars(username)
    filter_str = "(uid=" + safe_user + ")"
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with imported escape function",
                tags=["python", "import-escape", "secure"]
            ),

            DetectorValidationSample(
                name="ldap_python_hardcoded_filter",
                code='''
import ldap

def get_all_users():
    conn = ldap.initialize('ldap://localhost:389')
    # SECURE: Hardcoded filter, no user input
    filter_str = "(objectClass=person)"
    result = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, filter_str)
    return result
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure hardcoded filter (no user input)",
                tags=["python", "hardcoded", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="ldap_javascript_template_literal",
                code='''
const ldap = require('ldapjs');

function searchUser(username) {
    const client = ldap.createClient({ url: 'ldap://localhost:389' });
    // VULNERABLE: Template literal allows injection
    const filter = `(uid=${username})`;
    client.search('dc=example,dc=com', { filter, scope: 'sub' }, (err, res) => {
        // handle results
    });
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LDAP_INJECTION"],
                expected_score=(0, 2),
                description="LDAP injection via template literal",
                tags=["javascript", "template-literal", "critical"]
            ),

            DetectorValidationSample(
                name="ldap_javascript_string_concatenation",
                code='''
const ldap = require('ldapjs');

function authenticateUser(username, password) {
    const client = ldap.createClient({ url: 'ldap://localhost:389' });
    // VULNERABLE: String concatenation in filter
    const filter = '(uid=' + username + ')';
    client.search('dc=example,dc=com', { filter, scope: 'sub' }, (err, res) => {
        // handle results
    });
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LDAP_INJECTION"],
                expected_score=(0, 2),
                description="LDAP injection via string concatenation",
                tags=["javascript", "string-concat", "basic"]
            ),

            DetectorValidationSample(
                name="ldap_javascript_req_body_no_escaping",
                code='''
const express = require('express');
const ldap = require('ldapjs');
const app = express();

app.post('/search', (req, res) => {
    const username = req.body.username;
    const client = ldap.createClient({ url: 'ldap://localhost:389' });
    // VULNERABLE: User input from req.body without escaping
    const filter = `(uid=${username})`;
    client.search('dc=example,dc=com', { filter, scope: 'sub' }, (err, result) => {
        res.json(result);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LDAP_INJECTION"],
                expected_score=(0, 2),
                description="LDAP injection via req.body without escaping",
                tags=["javascript", "req-body", "critical"]
            ),

            DetectorValidationSample(
                name="ldap_javascript_req_params",
                code='''
const express = require('express');
const ldap = require('ldapjs');
const app = express();

app.get('/user/:username', (req, res) => {
    const client = ldap.createClient({ url: 'ldap://localhost:389' });
    // VULNERABLE: User input from req.params
    const filter = '(uid=' + req.params.username + ')';
    client.search('dc=example,dc=com', { filter, scope: 'sub' }, (err, result) => {
        res.json(result);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LDAP_INJECTION"],
                expected_score=(0, 2),
                description="LDAP injection via req.params",
                tags=["javascript", "req-params", "basic"]
            ),

            DetectorValidationSample(
                name="ldap_javascript_req_query",
                code='''
const express = require('express');
const ldap = require('ldapjs');
const app = express();

app.get('/search', (req, res) => {
    const email = req.query.email;
    const client = ldap.createClient({ url: 'ldap://localhost:389' });
    // VULNERABLE: User input from req.query
    const filter = `(mail=${email})`;
    client.search('dc=example,dc=com', { filter, scope: 'sub' }, (err, result) => {
        res.json(result);
    });
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["LDAP_INJECTION"],
                expected_score=(0, 2),
                description="LDAP injection via req.query",
                tags=["javascript", "req-query", "basic"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="ldap_javascript_ldap_escape",
                code='''
const ldap = require('ldapjs');
const ldapEscape = require('ldap-escape');

function searchUser(username) {
    const client = ldap.createClient({ url: 'ldap://localhost:389' });
    // SECURE: ldap-escape library sanitizes input
    const safeUsername = ldapEscape.filter(username);
    const filter = `(uid=${safeUsername})`;
    client.search('dc=example,dc=com', { filter, scope: 'sub' }, (err, res) => {
        // handle results
    });
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with ldap-escape library",
                tags=["javascript", "ldap-escape", "secure"]
            ),

            DetectorValidationSample(
                name="ldap_javascript_escape_ldap_filter",
                code='''
const ldap = require('ldapjs');

function escapeLdapFilter(str) {
    return str.replace(/[*()\\\\]/g, '\\\\$&');
}

function searchUser(username) {
    const client = ldap.createClient({ url: 'ldap://localhost:389' });
    // SECURE: Custom escaping function
    const safeUsername = escapeLdapFilter(username);
    const filter = `(uid=${safeUsername})`;
    client.search('dc=example,dc=com', { filter, scope: 'sub' }, (err, res) => {
        // handle results
    });
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with escapeLdapFilter function",
                tags=["javascript", "escape-function", "secure"]
            ),

            DetectorValidationSample(
                name="ldap_javascript_hardcoded_filter",
                code='''
const ldap = require('ldapjs');

function getAllUsers() {
    const client = ldap.createClient({ url: 'ldap://localhost:389' });
    // SECURE: Hardcoded filter, no user input
    const filter = '(objectClass=person)';
    client.search('dc=example,dc=com', { filter, scope: 'sub' }, (err, res) => {
        // handle results
    });
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure hardcoded filter (no user input)",
                tags=["javascript", "hardcoded", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="ldap_python_no_ldap_usage",
                code='''
def search_user(username):
    # SECURE: No LDAP usage at all
    return {"username": username}
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No LDAP usage (edge case)",
                tags=["python", "no-ldap", "edge-case", "secure"]
            ),

            DetectorValidationSample(
                name="ldap_javascript_no_ldap_usage",
                code='''
function searchUser(username) {
    // SECURE: No LDAP usage
    return { username: username };
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No LDAP usage (edge case)",
                tags=["javascript", "no-ldap", "edge-case", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLDAPInjectionDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All LDAP Injection detector validation tests PASSED")
        print("The LDAPInjectionDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} LDAP Injection detector validation tests FAILED")
        print("The LDAPInjectionDetector has accuracy issues that must be fixed.")
        sys.exit(1)
