#!/usr/bin/env python3
"""Test PHP file upload detection"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_file_upload import FileUploadDetector

def test_php_018():
    """Test php_018.php - WordPress plugin with insecure upload (vulnerable)"""
    code = Path("output/claude-sonnet-4-5/php_018.php").read_text()
    detector = FileUploadDetector()
    result = detector.analyze(code, "php")

    print("=" * 70)
    print("Test: php_018.php (WordPress upload - VULNERABLE)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:150]}...")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL vulnerability"
    print("\n✓ PASS: Correctly identified as VULNERABLE")

def test_php_user_supplied_mime():
    """Test vulnerable PHP code using $_FILES['file']['type'] (MIME spoofing)"""
    vulnerable_code = '''<?php
function handle_upload() {
    $file = $_FILES['profile_picture'];
    $allowed_types = ['image/jpeg', 'image/png'];

    // VULNERABLE: Trusts user-supplied MIME type
    if (!in_array($file['type'], $allowed_types)) {
        die('Invalid file type');
    }

    $upload_path = 'wp-content/uploads/' . basename($file['name']);
    move_uploaded_file($file['tmp_name'], $upload_path);
    echo "File uploaded successfully";
}
?>'''

    detector = FileUploadDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: Vulnerable PHP using $_FILES['file']['type'] (MIME spoofing)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:150]}...")

    assert result['score'] == 0, f"Expected score 0/2 (vulnerable), got {result['score']}/2"
    assert any(v['severity'] == 'CRITICAL' for v in result['vulnerabilities']), "Should detect CRITICAL MIME spoofing vulnerability"
    assert any('MIME SPOOFING' in str(v.get('description', '')) for v in result['vulnerabilities']), "Should mention MIME spoofing"
    print("\n✓ PASS: Correctly identified MIME spoofing vulnerability")

def test_php_secure_upload():
    """Test secure PHP code with proper validation"""
    secure_code = '''<?php
function handle_secure_upload() {
    $file = $_FILES['profile_picture'];
    $allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf'];
    $max_size = 5 * 1024 * 1024; // 5MB

    // Extension validation
    $filename = basename($file['name']);
    $extension = strtolower(pathinfo($filename, PATHINFO_EXTENSION));
    if (!in_array($extension, $allowed_extensions)) {
        die('Invalid extension');
    }

    // Size limit
    if ($file['size'] > $max_size) {
        die('File too large');
    }

    // Proper MIME type verification using magic bytes
    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $mime_type = finfo_file($finfo, $file['tmp_name']);
    finfo_close($finfo);

    $allowed_mimes = ['image/jpeg', 'image/png', 'application/pdf'];
    if (!in_array($mime_type, $allowed_mimes)) {
        die('Invalid MIME type');
    }

    // Filename sanitization with random name
    $new_filename = uniqid() . '.' . $extension;
    $upload_path = '/var/app_data/uploads/' . $new_filename;

    // Authorization check
    if (!is_user_logged_in() || !current_user_can('upload_files')) {
        die('Unauthorized');
    }

    move_uploaded_file($file['tmp_name'], $upload_path);
    echo "File uploaded securely";
}
?>'''

    detector = FileUploadDetector()
    result = detector.analyze(secure_code, "php")

    print("\n" + "=" * 70)
    print("Test: Secure PHP with proper validation")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:150]}...")

    assert result['score'] == 2, f"Expected score 2/2 (secure), got {result['score']}/2"
    assert any(v['type'] == 'SECURE' for v in result['vulnerabilities']), "Should detect SECURE pattern"
    print("\n✓ PASS: Correctly identified as SECURE")

def test_php_missing_size_limit():
    """Test PHP code missing file size limit (partial protection)"""
    partial_code = '''<?php
function handle_upload_no_size_limit() {
    $file = $_FILES['document'];
    $allowed_extensions = ['pdf', 'docx'];

    // Extension validation
    $filename = sanitize_file_name($file['name']);
    $extension = pathinfo($filename, PATHINFO_EXTENSION);
    if (!in_array($extension, $allowed_extensions)) {
        die('Invalid extension');
    }

    // Proper MIME type verification
    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $mime_type = finfo_file($finfo, $file['tmp_name']);
    finfo_close($finfo);

    // MISSING: File size limit

    move_uploaded_file($file['tmp_name'], 'uploads/' . $filename);
}
?>'''

    detector = FileUploadDetector()
    result = detector.analyze(partial_code, "php")

    print("\n" + "=" * 70)
    print("Test: PHP upload missing file size limit (partial protection)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:150]}...")

    assert result['score'] == 1, f"Expected score 1/2 (partial protection), got {result['score']}/2"
    assert any(v['severity'] == 'MEDIUM' for v in result['vulnerabilities']), "Should detect MEDIUM vulnerability"
    assert any('file size limits' in str(v.get('description', '')) for v in result['vulnerabilities']), "Should mention missing size limits"
    print("\n✓ PASS: Correctly identified as partially protected (MEDIUM)")

def test_php_web_root_storage():
    """Test PHP code storing files in web root (partial protection - MEDIUM)"""
    vulnerable_code = '''<?php
function upload_to_web_root() {
    $file = $_FILES['image'];
    $extension = pathinfo($file['name'], PATHINFO_EXTENSION);

    // Has: extension validation, filename sanitization
    // Missing: MIME verification, size limits
    // Stores in web-accessible directory (additional risk)
    $upload_path = 'wp-content/uploads/' . basename($file['name']);
    move_uploaded_file($file['tmp_name'], $upload_path);
}
?>'''

    detector = FileUploadDetector()
    result = detector.analyze(vulnerable_code, "php")

    print("\n" + "=" * 70)
    print("Test: PHP upload to web root (partial protection - MEDIUM)")
    print("=" * 70)
    print(f"Score: {result['score']}/2")
    print(f"Vulnerabilities: {len(result['vulnerabilities'])}")
    for v in result['vulnerabilities']:
        print(f"  - [{v['severity']}] {v['type']}: {v.get('description', '')[:150]}...")

    assert result['score'] == 1, f"Expected score 1/2 (partial protection), got {result['score']}/2"
    assert any(v['severity'] == 'MEDIUM' for v in result['vulnerabilities']), "Should detect MEDIUM vulnerability"
    print("\n✓ PASS: Correctly identified as partially protected (MEDIUM)")

if __name__ == "__main__":
    test_php_018()
    test_php_user_supplied_mime()
    test_php_secure_upload()
    test_php_missing_size_limit()
    test_php_web_root_storage()
    print("\n" + "=" * 70)
    print("All PHP upload tests passed!")
    print("=" * 70)
