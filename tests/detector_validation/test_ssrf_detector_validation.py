#!/usr/bin/env python3
"""
SSRF (Server-Side Request Forgery) Detector Validation Tests

This module validates that the SSRFDetector correctly identifies
SSRF vulnerabilities and secure URL fetching patterns.

Test Coverage:
- Python: requests, urllib with allowlist/IP validation
- JavaScript: fetch, axios with allowlist/scheme checks
- PHP: curl, file_get_contents with allowlist
- Validation layers: allowlist, scheme check, IP blocking
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_ssrf import SSRFDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestSSRFDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for SSRF Detector."""

    def get_detector(self):
        """Return SSRFDetector instance."""
        return SSRFDetector()

    def get_samples(self):
        """Return hand-crafted SSRF test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="ssrf_python_no_validation",
                code='''
import requests
from flask import Flask, request

app = Flask(__name__)

@app.route('/fetch')
def fetch_url():
    url = request.args.get('url')
    # VULNERABLE: No validation
    response = requests.get(url)
    return response.text
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF with no validation",
                tags=["python", "requests", "no-validation", "critical"]
            ),

            DetectorValidationSample(
                name="ssrf_python_scheme_only",
                code='''
import requests
from flask import Flask, request

app = Flask(__name__)

@app.route('/fetch')
def fetch_url():
    url = request.args.get('url')
    # VULNERABLE: Only scheme check (insufficient)
    if not url.startswith('http://') and not url.startswith('https://'):
        return "Invalid scheme", 400
    response = requests.get(url)
    return response.text
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF with scheme-only validation (still vulnerable)",
                tags=["python", "scheme-only", "partial-validation"]
            ),

            DetectorValidationSample(
                name="ssrf_python_urllib",
                code='''
import urllib.request
from flask import Flask, request

app = Flask(__name__)

@app.route('/download')
def download():
    url = request.args.get('url')
    # VULNERABLE: urllib without validation
    response = urllib.request.urlopen(url)
    return response.read()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF via urllib without validation",
                tags=["python", "urllib", "basic"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="ssrf_python_allowlist",
                code='''
import requests
from urllib.parse import urlparse
from flask import Flask, request

app = Flask(__name__)

ALLOWED_HOSTS = ['api.example.com', 'cdn.example.com']

@app.route('/fetch')
def fetch_url():
    url = request.args.get('url')
    # SECURE: Allowlist validation
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return "Host not allowed", 403

    response = requests.get(url)
    return response.text
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with allowlist validation",
                tags=["python", "allowlist", "secure"]
            ),

            DetectorValidationSample(
                name="ssrf_python_scheme_and_ip_blocking",
                code='''
import requests
import ipaddress
from urllib.parse import urlparse
from flask import Flask, request

app = Flask(__name__)

@app.route('/fetch')
def fetch_url():
    url = request.args.get('url')
    parsed = urlparse(url)

    # Scheme check
    if parsed.scheme not in ['http', 'https']:
        return "Invalid scheme", 400

    # IP blocking
    ip = ipaddress.ip_address(parsed.hostname)
    if ip.is_private or ip.is_loopback:
        return "Private IP not allowed", 403

    if parsed.hostname == '169.254.169.254':
        return "Metadata endpoint blocked", 403

    response = requests.get(url)
    return response.text
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(1, 2),
                description="Scheme + IP blocking (still missing allowlist)",
                tags=["python", "scheme-ip-blocking", "partial"]
            ),

            DetectorValidationSample(
                name="ssrf_python_hardcoded_url",
                code='''
import requests

def fetch_api():
    # SECURE: Hardcoded URL, no user input
    response = requests.get('https://api.example.com/data')
    return response.json()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure hardcoded URL (no user input)",
                tags=["python", "hardcoded", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="ssrf_javascript_fetch_no_validation",
                code='''
const express = require('express');
const app = express();

app.get('/proxy', async (req, res) => {
    const url = req.query.url;
    // VULNERABLE: No validation
    const response = await fetch(url);
    const data = await response.text();
    res.send(data);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF via fetch() without validation",
                tags=["javascript", "fetch", "no-validation"]
            ),

            DetectorValidationSample(
                name="ssrf_javascript_axios_concat",
                code='''
const axios = require('axios');
const express = require('express');
const app = express();

app.get('/data', async (req, res) => {
    const url = req.query.url;
    // VULNERABLE: axios with user input
    const response = await axios.get(url);
    res.json(response.data);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF via axios with user input",
                tags=["javascript", "axios", "basic"]
            ),

            DetectorValidationSample(
                name="ssrf_javascript_scheme_only",
                code='''
const express = require('express');
const app = express();

app.get('/fetch', async (req, res) => {
    const url = req.query.url;
    // VULNERABLE: Scheme check only (insufficient)
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        return res.status(400).send('Invalid scheme');
    }
    const response = await fetch(url);
    res.send(await response.text());
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF with scheme-only check (still vulnerable)",
                tags=["javascript", "scheme-only", "partial"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="ssrf_javascript_allowlist",
                code='''
const express = require('express');
const app = express();

const ALLOWED_HOSTS = ['api.example.com', 'cdn.example.com'];

app.get('/fetch', async (req, res) => {
    const url = req.query.url;
    // SECURE: Allowlist validation
    const urlObj = new URL(url);
    if (!ALLOWED_HOSTS.includes(urlObj.hostname)) {
        return res.status(403).send('Host not allowed');
    }

    const response = await fetch(url);
    res.send(await response.text());
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with allowlist validation",
                tags=["javascript", "allowlist", "secure"]
            ),

            DetectorValidationSample(
                name="ssrf_javascript_axios_allowlist",
                code='''
const axios = require('axios');

const allowedHosts = ['api.github.com', 'api.twitter.com'];

async function fetchExternal(url) {
    // SECURE: Hostname allowlist check
    const urlObj = new URL(url);
    if (!allowedHosts.includes(urlObj.hostname)) {
        throw new Error('Host not in allowlist');
    }

    const response = await axios.get(url);
    return response.data;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure axios with allowlist",
                tags=["javascript", "axios", "allowlist", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - PHP ==========

            DetectorValidationSample(
                name="ssrf_php_curl_no_validation",
                code='''
<?php
function fetch_url($url) {
    // VULNERABLE: No validation
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    curl_close($ch);
    return $response;
}

$url = $_GET['url'];
echo fetch_url($url);
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF via curl without validation",
                tags=["php", "curl", "no-validation"]
            ),

            DetectorValidationSample(
                name="ssrf_php_file_get_contents",
                code='''
<?php
$url = $_GET['url'];
// VULNERABLE: file_get_contents with user input
$content = file_get_contents($url);
echo $content;
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF via file_get_contents",
                tags=["php", "file-get-contents", "basic"]
            ),

            DetectorValidationSample(
                name="ssrf_php_scheme_only",
                code='''
<?php
$url = $_GET['url'];

// VULNERABLE: Scheme check only
$parsed = parse_url($url);
if ($parsed['scheme'] !== 'http' && $parsed['scheme'] !== 'https') {
    die('Invalid scheme');
}

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response = curl_exec($ch);
echo $response;
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF with scheme-only validation",
                tags=["php", "scheme-only", "partial"]
            ),

            # ========== SECURE SAMPLES - PHP ==========

            DetectorValidationSample(
                name="ssrf_php_allowlist",
                code='''
<?php
$ALLOWED_HOSTS = ['api.example.com', 'cdn.example.com'];

function fetch_url($url) {
    global $ALLOWED_HOSTS;

    // SECURE: Allowlist validation
    $parsed = parse_url($url);
    if (!in_array($parsed['host'], $ALLOWED_HOSTS)) {
        throw new Exception('Host not in allowlist');
    }

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    curl_close($ch);
    return $response;
}

$url = $_GET['url'];
echo fetch_url($url);
?>
''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure with allowlist validation",
                tags=["php", "allowlist", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="ssrf_python_function_parameter",
                code='''
import requests

def fetch_data(url):
    # VULNERABLE: Function parameter is user-controlled
    response = requests.get(url)
    return response.json()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF via function parameter",
                tags=["python", "function-param", "edge-case"]
            ),

            DetectorValidationSample(
                name="ssrf_javascript_destructuring",
                code='''
const express = require('express');
const app = express();

app.post('/proxy', async (req, res) => {
    // VULNERABLE: Destructuring from req.body
    const { url } = req.body;
    const response = await fetch(url);
    res.send(await response.text());
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(0, 2),
                description="SSRF via destructured parameter",
                tags=["javascript", "destructuring", "edge-case"]
            ),

            DetectorValidationSample(
                name="ssrf_python_ip_blocking_only",
                code='''
import requests
import ipaddress
from urllib.parse import urlparse
from flask import Flask, request

app = Flask(__name__)

@app.route('/fetch')
def fetch_url():
    url = request.args.get('url')
    parsed = urlparse(url)

    # IP blocking only (no scheme check)
    if parsed.hostname in ['127.0.0.1', 'localhost', '169.254.169.254']:
        return "Blocked IP", 403

    ip = ipaddress.ip_address(parsed.hostname)
    if ip.is_private:
        return "Private IP blocked", 403

    response = requests.get(url)
    return response.text
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SSRF"],
                expected_score=(1, 2),
                description="IP blocking without scheme check (partial)",
                tags=["python", "ip-blocking-only", "edge-case"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSSRFDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All SSRF detector validation tests PASSED")
        print("The SSRFDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} SSRF detector validation tests FAILED")
        print("The SSRFDetector has accuracy issues that must be fixed.")
        sys.exit(1)
