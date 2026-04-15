#!/usr/bin/env python3
"""
Php Upload Detector Validation Tests

This module validates that the FileUploadDetector correctly identifies
security vulnerabilities in PHP code.
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_file_upload import FileUploadDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestPhpUploadDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for FileUploadDetector (PHP)."""

    def get_detector(self):
        """Return FileUploadDetector instance."""
        return FileUploadDetector()

    def get_samples(self):
        """Return PHP security test samples for FileUploadDetector."""
        # PHP uses existing multi-language detectors
        # These samples test the PHP language support
        return [
            DetectorValidationSample(
                name="php_upload_no_validation",
                code='''<?php
function handle_upload() {
    if (isset($_FILES['file'])) {
        $target_path = "/var/www/uploads/" . $_FILES['file']['name'];
        move_uploaded_file($_FILES['file']['tmp_name'], $target_path);
        echo "File uploaded successfully";
    }
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="PHP file upload without validation (CRITICAL)",
                tags=["php", "move_uploaded_file", "no_validation", "critical"]
            ),
            DetectorValidationSample(
                name="php_upload_weak_extension_check",
                code='''<?php
function handle_image_upload() {
    if (isset($_FILES['image'])) {
        $filename = $_FILES['image']['name'];
        $ext = pathinfo($filename, PATHINFO_EXTENSION);

        if ($ext == "jpg" || $ext == "png") {
            $target = "/var/www/uploads/" . $filename;
            move_uploaded_file($_FILES['image']['tmp_name'], $target);
        }
    }
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="PHP upload with weak extension-only check (CRITICAL)",
                tags=["php", "move_uploaded_file", "weak_validation", "critical"]
            ),
            DetectorValidationSample(
                name="php_upload_user_controlled_path",
                code='''<?php
function save_document() {
    $upload_dir = $_POST['directory'];
    $filename = $_FILES['document']['name'];
    $target_path = $upload_dir . "/" . $filename;

    move_uploaded_file($_FILES['document']['tmp_name'], $target_path);
}
?>''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="PHP upload with user-controlled directory (CRITICAL)",
                tags=["php", "move_uploaded_file", "path_traversal", "critical"]
            ),
            DetectorValidationSample(
                name="php_safe_mime_type_validation",
                code='''<?php
function handle_image_upload() {
    if (isset($_FILES['image'])) {
        $allowed_types = ['image/jpeg', 'image/png', 'image/gif'];
        $file_info = finfo_open(FILEINFO_MIME_TYPE);
        $mime_type = finfo_file($file_info, $_FILES['image']['tmp_name']);
        finfo_close($file_info);

        if (!in_array($mime_type, $allowed_types)) {
            die('Invalid file type');
        }

        $safe_filename = bin2hex(random_bytes(16)) . '.jpg';
        $target = "/var/www/uploads/" . $safe_filename;
        move_uploaded_file($_FILES['image']['tmp_name'], $target);
    }
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP upload with MIME validation and random filename (SECURE)",
                tags=["php", "move_uploaded_file", "mime_validation", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_getimagesize_validation",
                code='''<?php
function handle_avatar_upload() {
    if (isset($_FILES['avatar'])) {
        $image_info = getimagesize($_FILES['avatar']['tmp_name']);

        if ($image_info === false) {
            die('File is not a valid image');
        }

        $allowed_types = [IMAGETYPE_JPEG, IMAGETYPE_PNG, IMAGETYPE_GIF];
        if (!in_array($image_info[2], $allowed_types)) {
            die('Invalid image type');
        }

        $ext = image_type_to_extension($image_info[2]);
        $safe_filename = uniqid('avatar_', true) . $ext;
        $target = "/var/www/uploads/avatars/" . $safe_filename;

        move_uploaded_file($_FILES['avatar']['tmp_name'], $target);
    }
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP upload with getimagesize validation (SECURE)",
                tags=["php", "move_uploaded_file", "getimagesize", "secure"]
            ),
            DetectorValidationSample(
                name="php_safe_comprehensive_validation",
                code='''<?php
function save_document() {
    if (!isset($_FILES['document'])) {
        return;
    }

    $allowed_extensions = ['pdf', 'doc', 'docx'];
    $allowed_mime = ['application/pdf', 'application/msword'];
    $max_size = 5 * 1024 * 1024; // 5MB

    $file = $_FILES['document'];

    if ($file['size'] > $max_size) {
        die('File too large');
    }

    $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
    if (!in_array($ext, $allowed_extensions)) {
        die('Invalid file extension');
    }

    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $mime = finfo_file($finfo, $file['tmp_name']);
    finfo_close($finfo);

    if (!in_array($mime, $allowed_mime)) {
        die('Invalid MIME type');
    }

    $safe_filename = bin2hex(random_bytes(16)) . '.' . $ext;
    $target_path = "/var/www/uploads/documents/" . $safe_filename;

    move_uploaded_file($file['tmp_name'], $target_path);
}
?>''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP upload with comprehensive validation (SECURE)",
                tags=["php", "move_uploaded_file", "comprehensive", "secure"]
            )
        ]


if __name__ == '__main__':
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhpUploadDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All Php Upload detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} tests FAILED")
        sys.exit(1)
