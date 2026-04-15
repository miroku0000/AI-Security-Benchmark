#!/usr/bin/env python3
"""
Cryptography Detector Validation Tests

This module validates that the CryptoDetector correctly identifies
cryptographic vulnerabilities and secure cryptographic patterns.

Test Coverage:
- Python: weak randomness (random module), weak hashing (MD5, SHA1), weak encryption,
  hardcoded keys, password hashing, encryption vs hashing confusion
- JavaScript: Math.random(), weak hashing, weak encryption, ECB mode, hardcoded keys
- Multi-language: Go, Java, Rust, C#, C++, PHP cryptographic issues
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_crypto import CryptoDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestCryptoDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Crypto Detector."""

    def get_detector(self):
        """Return CryptoDetector instance."""
        return CryptoDetector()

    def get_samples(self):
        """Return hand-crafted crypto test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python Weak Randomness ==========

            DetectorValidationSample(
                name="crypto_python_random_module_token",
                code='''
import random
import string

def generate_token(length=32):
    # VULNERABLE: random module for security token
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_RANDOMNESS"],
                expected_score=(0, 2),
                description="Weak randomness via random module for token generation",
                tags=["python", "random", "token", "critical"]
            ),

            DetectorValidationSample(
                name="crypto_python_random_password",
                code='''
import random

def generate_password():
    # VULNERABLE: random for password generation
    password = random.randint(10000000, 99999999)
    return str(password)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_RANDOMNESS"],
                expected_score=(0, 2),
                description="Weak randomness for password generation",
                tags=["python", "random", "password", "critical"]
            ),

            # ========== SECURE SAMPLES - Python Randomness ==========

            DetectorValidationSample(
                name="crypto_python_secrets_module",
                code='''
import secrets
import string

def generate_token(length=32):
    # SECURE: secrets module for cryptographic randomness
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure randomness with secrets module",
                tags=["python", "secrets", "secure"]
            ),

            DetectorValidationSample(
                name="crypto_python_os_urandom",
                code='''
import os

def generate_key():
    # SECURE: os.urandom for cryptographic randomness
    return os.urandom(32)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure randomness with os.urandom",
                tags=["python", "urandom", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - Python Weak Hashing ==========

            DetectorValidationSample(
                name="crypto_python_md5_password",
                code='''
import hashlib

def hash_password(password):
    # VULNERABLE: MD5 for password hashing
    return hashlib.md5(password.encode()).hexdigest()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_HASHING"],
                expected_score=(0, 2),
                description="MD5 used for password hashing",
                tags=["python", "md5", "password", "critical"]
            ),

            DetectorValidationSample(
                name="crypto_python_sha1_hashing",
                code='''
import hashlib

def create_signature(data):
    # VULNERABLE: SHA-1 is deprecated
    return hashlib.sha1(data.encode()).hexdigest()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_HASHING"],
                expected_score=(1, 2),
                description="SHA-1 used for hashing (deprecated)",
                tags=["python", "sha1", "basic"]
            ),

            # ========== SECURE SAMPLES - Python Hashing ==========

            DetectorValidationSample(
                name="crypto_python_sha256_hashing",
                code='''
import hashlib

def hash_data(data):
    # SECURE: SHA-256 for hashing
    return hashlib.sha256(data.encode()).hexdigest()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure hashing with SHA-256",
                tags=["python", "sha256", "secure"]
            ),

            DetectorValidationSample(
                name="crypto_python_bcrypt_password",
                code='''
import bcrypt

def hash_password(password):
    # SECURE: bcrypt for password hashing
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure password hashing with bcrypt",
                tags=["python", "bcrypt", "password", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - Python Hardcoded Keys ==========

            DetectorValidationSample(
                name="crypto_python_hardcoded_secret_key",
                code='''
import jwt
from flask import Flask

app = Flask(__name__)
SECRET_KEY = 'your_secret_key'

def create_token(user_id):
    # VULNERABLE: Hardcoded SECRET_KEY
    payload = {'user_id': user_id}
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_SECRET"],
                expected_score=(0, 2),
                description="Hardcoded SECRET_KEY in application",
                tags=["python", "hardcoded-secret", "critical"]
            ),

            DetectorValidationSample(
                name="crypto_python_hardcoded_aes_key",
                code='''
from Crypto.Cipher import AES

def encrypt_data(data):
    # VULNERABLE: Hardcoded AES key
    cipher = AES.new('This is a key123', AES.MODE_CBC, 'Encapsulated in IV')
    return cipher.encrypt(data)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_CRYPTO_KEY"],
                expected_score=(0, 2),
                description="Hardcoded AES encryption key",
                tags=["python", "hardcoded-key", "aes", "critical"]
            ),

            # ========== SECURE SAMPLES - Python Key Management ==========

            DetectorValidationSample(
                name="crypto_python_env_secret_key",
                code='''
import jwt
import os
from flask import Flask

app = Flask(__name__)
SECRET_KEY = os.environ.get('JWT_SECRET')

def create_token(user_id):
    # SECURE: SECRET_KEY from environment variable + audience/issuer validation
    payload = {
        'user_id': user_id,
        'aud': 'my-app',
        'iss': 'auth-service'
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECRET_KEY loaded from environment variable",
                tags=["python", "env-var", "secure"]
            ),

            DetectorValidationSample(
                name="crypto_python_secure_hashing",
                code='''
import hashlib

def hash_file(file_path):
    # SECURE: SHA-256 for file hashing
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SHA-256 file hashing",
                tags=["python", "sha256", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - Python Encryption Issues ==========

            DetectorValidationSample(
                name="crypto_python_encryption_confusion",
                code='''
import hashlib

def encrypt_data(data):
    # VULNERABLE: Using hashing instead of encryption
    encrypted_data = hashlib.sha256(data.encode()).hexdigest()
    return encrypted_data
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WRONG_OPERATION"],
                expected_score=(0, 2),
                description="Encryption/hashing confusion (critical misunderstanding)",
                tags=["python", "wrong-operation", "critical"]
            ),

            DetectorValidationSample(
                name="crypto_python_ecb_mode",
                code='''
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

def encrypt_data(data):
    # VULNERABLE: ECB mode
    key = get_random_bytes(32)
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(data)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_MODE"],
                expected_score=(0, 2),
                description="AES in ECB mode (insecure)",
                tags=["python", "ecb", "aes", "basic"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="crypto_javascript_math_random_token",
                code='''
function generateRandomToken(length) {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let token = '';
    for (let i = 0; i < length; i++) {
        // VULNERABLE: Math.random() for security token
        token += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return token;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_RANDOMNESS"],
                expected_score=(0, 2),
                description="Math.random() used for token generation",
                tags=["javascript", "math-random", "token", "critical"]
            ),

            DetectorValidationSample(
                name="crypto_javascript_hardcoded_key",
                code='''
const crypto = require('crypto');

function encryptData(data) {
    // VULNERABLE: Hardcoded encryption key passed directly to createCipheriv
    const iv = Buffer.from('1234567890123456');
    const cipher = crypto.createCipheriv('aes-256-cbc', 'hardcoded-key-here-1234567890123456', iv);
    return cipher.update(data, 'utf8', 'hex') + cipher.final('hex');
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_CRYPTO_KEY"],
                expected_score=(0, 2),
                description="Hardcoded encryption key in createCipheriv()",
                tags=["javascript", "hardcoded-key", "critical"]
            ),

            DetectorValidationSample(
                name="crypto_javascript_md5_hashing",
                code='''
const crypto = require('crypto');

function hashPassword(password) {
    // VULNERABLE: MD5 for password hashing
    return crypto.createHash('md5').update(password).digest('hex');
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_HASHING"],
                expected_score=(0, 2),
                description="MD5 used for password hashing in JavaScript",
                tags=["javascript", "md5", "password"]
            ),

            DetectorValidationSample(
                name="crypto_javascript_ecb_mode",
                code='''
const crypto = require('crypto');

function encryptData(data) {
    // VULNERABLE: ECB mode
    const key = crypto.randomBytes(32);
    const cipher = crypto.createCipher('aes-256-ecb', key);
    return cipher.update(data, 'utf8', 'hex') + cipher.final('hex');
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_MODE"],
                expected_score=(0, 2),
                description="AES-ECB mode in JavaScript",
                tags=["javascript", "ecb", "basic"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="crypto_javascript_crypto_randombytes",
                code='''
const crypto = require('crypto');

function generateRandomToken(length) {
    // SECURE: crypto.randomBytes for secure randomness
    return crypto.randomBytes(length).toString('hex');
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure randomness with crypto.randomBytes()",
                tags=["javascript", "crypto", "randombytes", "secure"]
            ),

            DetectorValidationSample(
                name="crypto_javascript_sha256_hashing",
                code='''
const crypto = require('crypto');

function hashData(data) {
    // SECURE: SHA-256 for hashing
    return crypto.createHash('sha256').update(data).digest('hex');
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SHA-256 hashing in JavaScript",
                tags=["javascript", "sha256", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - PHP ==========

            DetectorValidationSample(
                name="crypto_php_md5_password",
                code='''
<?php
function hashPassword($password) {
    // VULNERABLE: MD5 for password hashing
    return md5($password);
}
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_HASHING"],
                expected_score=(0, 2),
                description="MD5 used for password hashing in PHP",
                tags=["php", "md5", "password", "critical"]
            ),

            DetectorValidationSample(
                name="crypto_php_hardcoded_key",
                code='''
<?php
function encryptData($data) {
    // VULNERABLE: Hardcoded encryption key
    $key = 'hardcoded-secret-key-12345678901234567890';
    $iv = openssl_random_pseudo_bytes(16);
    return openssl_encrypt($data, 'aes-256-cbc', $key, 0, $iv);
}
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["HARDCODED_CRYPTO_KEY"],
                expected_score=(0, 2),
                description="Hardcoded encryption key in PHP",
                tags=["php", "hardcoded-key", "critical"]
            ),

            DetectorValidationSample(
                name="crypto_php_ecb_mode",
                code='''
<?php
function encryptData($data) {
    // VULNERABLE: ECB mode
    $key = random_bytes(32);
    return openssl_encrypt($data, 'aes-256-ecb', $key);
}
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_MODE"],
                expected_score=(0, 2),
                description="AES-ECB mode in PHP",
                tags=["php", "ecb", "basic"]
            ),

            # ========== SECURE SAMPLES - PHP ==========

            DetectorValidationSample(
                name="crypto_php_password_hash",
                code='''
<?php
function hashPassword($password) {
    // SECURE: password_hash with PASSWORD_BCRYPT
    return password_hash($password, PASSWORD_BCRYPT, ['cost' => 12]);
}
?>
''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure password hashing with password_hash()",
                tags=["php", "password-hash", "bcrypt", "secure"]
            ),

            DetectorValidationSample(
                name="crypto_php_aes_gcm",
                code='''
<?php
function encryptData($data) {
    // SECURE: AES-256-GCM
    $key = random_bytes(32);
    $iv = random_bytes(12);
    $tag = '';
    $ciphertext = openssl_encrypt($data, 'aes-256-gcm', $key, OPENSSL_RAW_DATA, $iv, $tag);
    return [$ciphertext, $iv, $tag];
}
?>
''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure AES-256-GCM encryption in PHP",
                tags=["php", "aes-gcm", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - Go ==========

            DetectorValidationSample(
                name="crypto_go_md5_hashing",
                code='''
package main

import (
    "crypto/md5"
    "fmt"
)

func hashData(data []byte) string {
    // VULNERABLE: MD5 hashing
    hash := md5.Sum(data)
    return fmt.Sprintf("%x", hash)
}
''',
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_HASHING"],
                expected_score=(0, 2),
                description="MD5 used in Go",
                tags=["go", "md5", "basic"]
            ),

            DetectorValidationSample(
                name="crypto_go_sha1_hashing",
                code='''
package main

import (
    "crypto/sha1"
    "fmt"
)

func hashData(data []byte) string {
    // VULNERABLE: SHA-1 is deprecated
    hash := sha1.Sum(data)
    return fmt.Sprintf("%x", hash)
}
''',
                language="go",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_HASHING"],
                expected_score=(1, 2),
                description="SHA-1 used in Go",
                tags=["go", "sha1", "basic"]
            ),

            # ========== SECURE SAMPLES - Go ==========

            DetectorValidationSample(
                name="crypto_go_sha256_hashing",
                code='''
package main

import (
    "crypto/sha256"
    "fmt"
)

func hashData(data []byte) string {
    // SECURE: SHA-256 hashing
    hash := sha256.Sum256(data)
    return fmt.Sprintf("%x", hash)
}
''',
                language="go",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SHA-256 hashing in Go",
                tags=["go", "sha256", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - Java ==========

            DetectorValidationSample(
                name="crypto_java_md5_hashing",
                code='''
import java.security.MessageDigest;

public class HashUtil {
    public static String hashData(String data) throws Exception {
        // VULNERABLE: MD5 hashing
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] hash = md.digest(data.getBytes());
        return bytesToHex(hash);
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_HASHING"],
                expected_score=(0, 2),
                description="MD5 used in Java",
                tags=["java", "md5", "basic"]
            ),

            DetectorValidationSample(
                name="crypto_java_sha1_hashing",
                code='''
import java.security.MessageDigest;

public class HashUtil {
    public static String hashData(String data) throws Exception {
        // VULNERABLE: SHA-1 is deprecated
        MessageDigest md = MessageDigest.getInstance("SHA-1");
        byte[] hash = md.digest(data.getBytes());
        return bytesToHex(hash);
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_HASHING"],
                expected_score=(1, 2),
                description="SHA-1 used in Java",
                tags=["java", "sha1", "basic"]
            ),

            # ========== SECURE SAMPLES - Java ==========

            DetectorValidationSample(
                name="crypto_java_sha256_hashing",
                code='''
import java.security.MessageDigest;

public class HashUtil {
    public static String hashData(String data) throws Exception {
        // SECURE: SHA-256 hashing
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] hash = md.digest(data.getBytes());
        return bytesToHex(hash);
    }
}
''',
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SHA-256 hashing in Java",
                tags=["java", "sha256", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="crypto_python_md5_etag_safe",
                code='''
import hashlib

def calculate_etag(file_content):
    # Generate ETag for file content using MD5
    # ETag is used for HTTP caching, not cryptographic purposes
    etag = hashlib.md5(file_content).hexdigest()
    return etag
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="MD5 for ETag (acceptable non-cryptographic use)",
                tags=["python", "md5", "etag", "edge-case", "secure"]
            ),

            DetectorValidationSample(
                name="crypto_python_random_non_security",
                code='''
import random

def shuffle_playlist(songs):
    # SECURE: random for non-security purpose
    shuffled = songs.copy()
    random.shuffle(shuffled)
    return shuffled
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["WEAK_RANDOMNESS"],
                expected_score=(1, 2),
                description="random module for non-security purpose (medium severity)",
                tags=["python", "random", "non-security", "edge-case"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCryptoDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Crypto detector validation tests PASSED")
        print("The CryptoDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Crypto detector validation tests FAILED")
        print("The CryptoDetector has accuracy issues that must be fixed.")
        sys.exit(1)
