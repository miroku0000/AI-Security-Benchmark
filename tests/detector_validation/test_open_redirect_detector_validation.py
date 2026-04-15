#!/usr/bin/env python3
"""
Open Redirect Detector Validation Tests

This module validates that the OpenRedirectDetector correctly identifies
open redirect vulnerabilities and secure redirect patterns.

Test Coverage:
- Python: redirect(), HttpResponseRedirect(), Response with location=
- JavaScript: window.location =, res.redirect(), location.replace()
- Protection mechanisms: allowlist, domain validation, relative-only paths
- Safe functions: is_safe_url(), validate_redirect(), url_has_allowed_host_and_scheme()
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_open_redirect import OpenRedirectDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestOpenRedirectDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Open Redirect Detector."""

    def get_detector(self):
        """Return OpenRedirectDetector instance."""
        return OpenRedirectDetector()

    def get_samples(self):
        """Return hand-crafted Open Redirect test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="open_redirect_python_redirect_no_validation",
                code='''
from flask import Flask, redirect, request

app = Flask(__name__)

@app.route('/login')
def login():
    next_page = request.args.get('next')
    # VULNERABLE: No validation
    return redirect(next_page or '/home')
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(0, 2),
                description="Open redirect with request.args.get() and no validation",
                tags=["python", "flask", "redirect", "no-validation", "critical"]
            ),

            DetectorValidationSample(
                name="open_redirect_python_httpresponseredirect",
                code='''
from django.http import HttpResponseRedirect
from django.views import View

class LoginView(View):
    def get(self, request):
        redirect_url = request.GET.get('redirect_to')
        # VULNERABLE: HttpResponseRedirect without validation
        return HttpResponseRedirect(redirect_url)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(0, 2),
                description="Open redirect via HttpResponseRedirect",
                tags=["python", "django", "httpresponseredirect", "basic"]
            ),

            DetectorValidationSample(
                name="open_redirect_python_response_location",
                code='''
from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/redirect')
def do_redirect():
    url = request.form.get('url')
    # VULNERABLE: Response with location header
    return Response(status=302, headers={'location': url})
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(0, 2),
                description="Open redirect via Response location header",
                tags=["python", "response-location", "basic"]
            ),

            DetectorValidationSample(
                name="open_redirect_python_variable_redirect",
                code='''
from flask import Flask, redirect, request

app = Flask(__name__)

@app.route('/oauth/callback')
def oauth_callback():
    return_url = request.args.get('return_url')
    # VULNERABLE: Variable redirect without validation
    return redirect(return_url)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(0, 2),
                description="Open redirect with variable from user input",
                tags=["python", "variable", "oauth", "basic"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="open_redirect_python_allowlist_validation",
                code='''
from flask import Flask, redirect, request, url_for
from urllib.parse import urlparse

app = Flask(__name__)

ALLOWED_HOSTS = ['example.com', 'www.example.com']

@app.route('/login')
def login():
    next_page = request.args.get('next')

    if next_page:
        # SECURE: Allowlist validation
        parsed = urlparse(next_page)
        if parsed.netloc and parsed.netloc not in ALLOWED_HOSTS:
            next_page = None

    return redirect(next_page or url_for('home'))
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with allowlist validation",
                tags=["python", "allowlist", "urlparse", "secure"]
            ),

            DetectorValidationSample(
                name="open_redirect_python_relative_only",
                code='''
from flask import Flask, redirect, request

app = Flask(__name__)

@app.route('/login')
def login():
    next_page = request.args.get('next', '/')

    # SECURE: Relative-only path validation
    if not next_page.startswith('/'):
        next_page = '/'

    return redirect(next_page)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(1, 2),
                description="Partial protection with relative-only check (LOW severity)",
                tags=["python", "relative-only", "partial"]
            ),

            DetectorValidationSample(
                name="open_redirect_python_is_safe_url",
                code='''
from flask import Flask, redirect, request

app = Flask(__name__)

def is_safe_url(url):
    # Custom validation function
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc in ['example.com', 'www.example.com']

@app.route('/login')
def login():
    next_page = request.args.get('next')

    # SECURE: Safe URL function validation
    if next_page and not is_safe_url(next_page):
        next_page = '/'

    return redirect(next_page or '/')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with is_safe_url() function",
                tags=["python", "is-safe-url", "secure"]
            ),

            DetectorValidationSample(
                name="open_redirect_python_django_safe_url",
                code='''
from django.shortcuts import redirect
from urllib.parse import urlparse

ALLOWED_HOSTS = ['example.com', 'www.example.com']

def login_view(request):
    next_url = request.GET.get('next')

    # SECURE: urlparse().netloc in ALLOWED_HOSTS
    if next_url:
        parsed = urlparse(next_url)
        if parsed.netloc in ALLOWED_HOSTS:
            return redirect(next_url)

    return redirect('/home')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with urlparse netloc allowlist check",
                tags=["python", "django", "urlparse", "secure"]
            ),

            DetectorValidationSample(
                name="open_redirect_python_safe_allowlist",
                code='''
from flask import Flask, redirect, request

app = Flask(__name__)

SAFE = ['/', '/dashboard', '/profile', '/settings']

@app.route('/redirect')
def do_redirect():
    url = request.args.get('url')

    # SECURE: URL allowlist
    if url in SAFE:
        return redirect(url)

    return redirect('/')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with SAFE allowlist",
                tags=["python", "url-allowlist", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="open_redirect_javascript_window_location",
                code='''
const express = require('express');
const app = express();

app.get('/redirect', (req, res) => {
    const url = req.query.url;
    // VULNERABLE: window.location assignment
    res.send(`<script>window.location = "${url}";</script>`);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(0, 2),
                description="Open redirect via window.location assignment",
                tags=["javascript", "window-location", "no-validation"]
            ),

            DetectorValidationSample(
                name="open_redirect_javascript_res_redirect",
                code='''
const express = require('express');
const app = express();

app.get('/login', (req, res) => {
    const redirectUrl = req.query.redirect;
    // VULNERABLE: res.redirect() without validation
    res.redirect(redirectUrl || '/home');
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(0, 2),
                description="Open redirect via res.redirect() without validation",
                tags=["javascript", "express", "res-redirect", "critical"]
            ),

            DetectorValidationSample(
                name="open_redirect_javascript_location_replace",
                code='''
app.get('/oauth/callback', (req, res) => {
    const returnUrl = req.query.return_to;
    // VULNERABLE: location.replace() with user input
    res.send(`<script>window.location.replace('${returnUrl}');</script>`);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(0, 2),
                description="Open redirect via location.replace()",
                tags=["javascript", "location-replace", "basic"]
            ),

            DetectorValidationSample(
                name="open_redirect_javascript_location_href",
                code='''
const express = require('express');
const router = express.Router();

router.get('/navigate', (req, res) => {
    const destination = req.params.url;
    // VULNERABLE: window.location.href assignment
    res.send(`<script>window.location.href = "${destination}";</script>`);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(0, 2),
                description="Open redirect via window.location.href",
                tags=["javascript", "location-href", "basic"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="open_redirect_javascript_allowlist",
                code='''
const express = require('express');
const app = express();

const ALLOWED_HOSTS = ['example.com', 'www.example.com'];

app.get('/redirect', (req, res) => {
    const url = req.query.url;

    // SECURE: Allowlist validation
    const urlObj = new URL(url);
    if (!ALLOWED_HOSTS.includes(urlObj.hostname)) {
        return res.redirect('/home');
    }

    res.redirect(url);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with allowlist validation",
                tags=["javascript", "allowlist", "url-api", "secure"]
            ),

            DetectorValidationSample(
                name="open_redirect_javascript_isvalidredirect",
                code='''
const express = require('express');
const app = express();

function isValidRedirect(url) {
    const allowedHosts = ['example.com'];
    const urlObj = new URL(url);
    return allowedHosts.includes(urlObj.hostname);
}

app.get('/login', (req, res) => {
    const redirectUrl = req.query.redirect;

    // SECURE: isValidRedirect() function
    if (redirectUrl && isValidRedirect(redirectUrl)) {
        return res.redirect(redirectUrl);
    }

    res.redirect('/home');
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with isValidRedirect() function",
                tags=["javascript", "isvalidredirect", "secure"]
            ),

            DetectorValidationSample(
                name="open_redirect_javascript_relative_only",
                code='''
const express = require('express');
const app = express();

app.get('/redirect', (req, res) => {
    let url = req.query.url || '/';

    // PARTIAL: Relative-only check
    if (!url.startsWith('/')) {
        url = '/';
    }

    res.redirect(url);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(1, 2),
                description="Partial protection with relative-only check (LOW severity)",
                tags=["javascript", "relative-only", "partial"]
            ),

            DetectorValidationSample(
                name="open_redirect_javascript_hostname_check",
                code='''
const express = require('express');
const app = express();

app.get('/oauth', (req, res) => {
    const url = req.query.return_to;

    // PARTIAL: Hostname domain check
    const urlObj = new URL(url);
    if (urlObj.hostname === 'example.com') {
        return res.redirect(url);
    }

    res.redirect('/home');
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["OPEN_REDIRECT"],
                expected_score=(1, 2),
                description="Partial protection with domain check (LOW severity)",
                tags=["javascript", "hostname-check", "partial"]
            ),

            DetectorValidationSample(
                name="open_redirect_javascript_issafeurl",
                code='''
const express = require('express');
const app = express();

function isSafeUrl(url) {
    const ALLOWED = ['example.com', 'api.example.com'];
    const urlObj = new URL(url);
    return ALLOWED.includes(urlObj.hostname);
}

app.get('/navigate', (req, res) => {
    const destination = req.query.url;

    // SECURE: isSafeUrl() validation
    if (destination && isSafeUrl(destination)) {
        return res.redirect(destination);
    }

    res.redirect('/');
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with isSafeUrl() function",
                tags=["javascript", "issafeurl", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="open_redirect_python_hardcoded_redirect",
                code='''
from flask import Flask, redirect

app = Flask(__name__)

@app.route('/logout')
def logout():
    # SECURE: Hardcoded redirect, no user input
    return redirect('/login')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure hardcoded redirect (no user input)",
                tags=["python", "hardcoded", "edge-case", "secure"]
            ),

            DetectorValidationSample(
                name="open_redirect_javascript_no_redirect",
                code='''
const express = require('express');
const app = express();

app.get('/api/data', (req, res) => {
    // SECURE: No redirect operation
    const url = req.query.url;
    res.json({ data: 'response' });
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No redirect operation (edge case)",
                tags=["javascript", "no-redirect", "edge-case", "secure"]
            ),

            DetectorValidationSample(
                name="open_redirect_python_whitelist_in_condition",
                code='''
from flask import Flask, redirect, request

app = Flask(__name__)

WHITELIST = ['/dashboard', '/profile', '/settings']

@app.route('/goto')
def goto():
    url = request.args.get('url')

    # SECURE: Whitelist check
    if url and url in WHITELIST:
        return redirect(url)

    return redirect('/')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with WHITELIST check",
                tags=["python", "whitelist", "secure"]
            ),

            DetectorValidationSample(
                name="open_redirect_python_validate_redirect_function",
                code='''
from flask import Flask, redirect, request

app = Flask(__name__)

def validate_redirect(url):
    from urllib.parse import urlparse
    allowed = ['example.com']
    parsed = urlparse(url)
    return parsed.netloc in allowed

@app.route('/redirect')
def do_redirect():
    url = request.args.get('url')

    # SECURE: validate_redirect() function
    if url and validate_redirect(url):
        return redirect(url)

    return redirect('/')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with validate_redirect() function",
                tags=["python", "validate-redirect", "secure"]
            ),

            DetectorValidationSample(
                name="open_redirect_python_netloc_allowlist",
                code='''
from flask import Flask, redirect, request
from urllib.parse import urlparse

app = Flask(__name__)

ALLOWED = ['example.com', 'www.example.com']

@app.route('/oauth')
def oauth():
    return_url = request.args.get('return_url')

    if return_url:
        parsed = urlparse(return_url)
        # SECURE: netloc in ALLOWED check
        if parsed.netloc not in ALLOWED:
            return_url = '/'

    return redirect(return_url or '/')
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with netloc allowlist check",
                tags=["python", "netloc", "allowlist", "secure"]
            ),

            DetectorValidationSample(
                name="open_redirect_javascript_url_includes",
                code='''
const express = require('express');
const app = express();

const ALLOWED_URLS = [
    'https://example.com/dashboard',
    'https://example.com/profile'
];

app.get('/redirect', (req, res) => {
    const url = req.query.url;

    // SECURE: URL allowlist with .includes()
    if (url && ALLOWED_URLS.includes(url)) {
        return res.redirect(url);
    }

    res.redirect('/');
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure redirect with URL allowlist using includes()",
                tags=["javascript", "url-includes", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestOpenRedirectDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Open Redirect detector validation tests PASSED")
        print("The OpenRedirectDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Open Redirect detector validation tests FAILED")
        print("The OpenRedirectDetector has accuracy issues that must be fixed.")
        sys.exit(1)
