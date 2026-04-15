"""
Validation tests for File Upload detector.

This module tests the File Upload detector against known vulnerable and secure code samples
to ensure it correctly identifies file upload vulnerabilities across Python, JavaScript, and PHP.
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_file_upload import FileUploadDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestFileUploadDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for the File Upload detector."""

    def get_detector(self):
        """Return an instance of the File Upload detector."""
        return FileUploadDetector()

    def get_samples(self):
        """Return a list of test samples for validating the File Upload detector."""
        return [
            # =================================================================
            # PYTHON - VULNERABLE SAMPLES
            # =================================================================

            DetectorValidationSample(
                name="python_no_extension_check",
                code='''from flask import Flask, request
import os

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file'
    file = request.files['file']
    file.save(os.path.join('uploads', file.filename))
    return 'File uploaded'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="Python file upload with no extension validation",
                tags=["python", "flask", "missing_extension_check"]
            ),

            DetectorValidationSample(
                name="python_no_mime_check",
                code='''from flask import Flask, request
import os

app = Flask(__name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file'
    file = request.files['file']
    if file and allowed_file(file.filename):
        file.save(os.path.join('uploads', file.filename))
        return 'File uploaded'
    return 'Invalid file'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="Python file upload missing 3 protections: MIME check, size limit, filename sanitization (CRITICAL)",
                tags=["python", "flask", "missing_mime_check", "missing_size_limit", "missing_sanitization", "critical"]
            ),

            DetectorValidationSample(
                name="python_mime_spoofing",
                code='''from flask import Flask, request
import os

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file'
    file = request.files['file']

    # Trusting client-provided MIME type - CRITICAL vulnerability
    if file.mimetype not in ['image/png', 'image/jpeg']:
        return 'Invalid file type'

    file.save(os.path.join('uploads', file.filename))
    return 'File uploaded'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="Python file upload trusting client-provided MIME type (spoofing vulnerability)",
                tags=["python", "flask", "mime_spoofing", "critical"]
            ),

            DetectorValidationSample(
                name="python_missing_size_and_sanitization",
                code='''from flask import Flask, request
import os
import magic

app = Flask(__name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file'
    file = request.files['file']

    # Extension check - YES
    if not allowed_file(file.filename):
        return 'Invalid extension'

    # MIME check using magic - YES
    file_data = file.read()
    mime = magic.from_buffer(file_data, mime=True)
    if mime not in ['image/png', 'image/jpeg']:
        return 'Invalid file type'

    # NO size limit check - MISSING
    # NO filename sanitization - MISSING (path traversal risk)
    file.save(os.path.join('uploads', file.filename))
    return 'File uploaded'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(1, 2),
                description="Python file upload missing 2 protections: size limit and filename sanitization (MEDIUM)",
                tags=["python", "flask", "missing_size_limit", "missing_sanitization", "medium"]
            ),

            # =================================================================
            # PYTHON - SECURE SAMPLES
            # =================================================================

            DetectorValidationSample(
                name="python_all_protections",
                code='''from flask import Flask, request
from werkzeug.utils import secure_filename
import os
import magic

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_MIMES = {'image/png', 'image/jpeg', 'image/gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file'

    file = request.files['file']

    # Extension validation
    if not allowed_file(file.filename):
        return 'Invalid extension'

    # MIME type verification using magic
    file_data = file.read()
    mime = magic.from_buffer(file_data, mime=True)
    if mime not in ALLOWED_MIMES:
        return 'Invalid file type'

    # Size limit (handled by MAX_CONTENT_LENGTH)

    # Filename sanitization
    filename = secure_filename(file.filename)

    file.save(os.path.join('uploads', filename))
    return 'File uploaded successfully'
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Python file upload with all 4 protections: extension check, MIME verification, size limit, and filename sanitization",
                tags=["python", "flask", "secure", "all_protections"]
            ),

            DetectorValidationSample(
                name="python_secure_with_finfo",
                code='''from flask import Flask, request
from werkzeug.utils import secure_filename
import os
import magic

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if not file:
        return 'No file'

    # All 4 protections
    if not allowed_file(file.filename):
        return 'Invalid extension'

    file_data = file.read()
    mime = magic.from_buffer(file_data, mime=True)
    if mime not in ['application/pdf', 'application/msword']:
        return 'Invalid MIME type'

    filename = secure_filename(file.filename)
    file.save(os.path.join('/var/uploads', filename))
    return 'Success'
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Python secure file upload with proper MIME verification",
                tags=["python", "flask", "secure", "magic"]
            ),

            # =================================================================
            # JAVASCRIPT - VULNERABLE SAMPLES
            # =================================================================

            DetectorValidationSample(
                name="javascript_no_file_filter",
                code='''const express = require('express');
const multer = require('multer');
const app = express();

const upload = multer({ dest: 'uploads/' });

app.post('/upload', upload.single('file'), (req, res) => {
    res.send('File uploaded');
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="JavaScript file upload with no fileFilter (accepts any file type)",
                tags=["javascript", "multer", "missing_file_filter"]
            ),

            DetectorValidationSample(
                name="javascript_infinite_size_limit",
                code='''const express = require('express');
const multer = require('multer');
const path = require('path');
const app = express();

const storage = multer.diskStorage({
    destination: 'uploads/',
    filename: (req, file, cb) => {
        cb(null, Date.now() + path.extname(file.originalname));
    }
});

const upload = multer({
    storage: storage,
    limits: { fileSize: Infinity },  // CRITICAL: No size limit
    fileFilter: (req, file, cb) => {
        const allowedTypes = /jpeg|jpg|png|gif/;
        const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
        if (extname) {
            cb(null, true);
        } else {
            cb(new Error('Invalid file type'));
        }
    }
});

app.post('/upload', upload.single('image'), (req, res) => {
    res.send('File uploaded');
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="JavaScript file upload with fileSize: Infinity (critical vulnerability)",
                tags=["javascript", "multer", "infinite_size", "critical"]
            ),

            DetectorValidationSample(
                name="javascript_missing_mime_and_sanitization",
                code='''const express = require('express');
const multer = require('multer');
const path = require('path');
const app = express();

const upload = multer({
    dest: 'uploads/',
    limits: { fileSize: 5 * 1024 * 1024 },  // 5MB - HAS size limit
    fileFilter: (req, file, cb) => {
        // HAS extension check
        const ext = path.extname(file.originalname).toLowerCase();
        if (['.jpg', '.png', '.gif'].includes(ext)) {
            cb(null, true);
        } else {
            cb(new Error('Invalid extension'));
        }
        // MISSING: MIME type verification
        // MISSING: Filename sanitization
    }
});

app.post('/upload', upload.single('file'), (req, res) => {
    res.send('File uploaded');
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(1, 2),
                description="JavaScript file upload missing 2 protections: MIME verification and filename sanitization (MEDIUM)",
                tags=["javascript", "multer", "missing_mime_check", "missing_sanitization", "medium"]
            ),

            DetectorValidationSample(
                name="javascript_svg_with_missing_protections",
                code='''const express = require('express');
const multer = require('multer');
const path = require('path');
const app = express();

const upload = multer({
    dest: 'uploads/',
    fileFilter: (req, file, cb) => {
        // Allowing SVG files - can contain XSS payloads
        const allowedTypes = /jpeg|jpg|png|gif|svg/;
        const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
        const mimetype = allowedTypes.test(file.mimetype);
        if (extname && mimetype) {
            cb(null, true);
        } else {
            cb(new Error('Invalid file type'));
        }
    }
    // Missing: size limits, filename sanitization
});

app.post('/upload', upload.single('image'), (req, res) => {
    res.send('File uploaded');
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(1, 2),
                description="JavaScript file upload missing 2 protections: size limit and filename sanitization (MEDIUM)",
                tags=["javascript", "multer", "missing_size_limit", "missing_sanitization", "medium"]
            ),

            # =================================================================
            # JAVASCRIPT - SECURE SAMPLES
            # =================================================================

            DetectorValidationSample(
                name="javascript_all_protections",
                code='''const express = require('express');
const multer = require('multer');
const path = require('path');
const fileType = require('file-type');
const fs = require('fs').promises;
const app = express();

const storage = multer.diskStorage({
    destination: 'uploads/',
    filename: (req, file, cb) => {
        // Sanitized filename
        const sanitized = file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_');
        cb(null, Date.now() + '-' + sanitized);
    }
});

const upload = multer({
    storage: storage,
    limits: { fileSize: 10 * 1024 * 1024 },  // 10MB size limit
    fileFilter: async (req, file, cb) => {
        // Extension validation
        const allowedExts = ['.jpg', '.jpeg', '.png'];
        const ext = path.extname(file.originalname).toLowerCase();
        if (!allowedExts.includes(ext)) {
            return cb(new Error('Invalid extension'));
        }

        // MIME type validation
        const allowedMimes = ['image/jpeg', 'image/png'];
        if (!allowedMimes.includes(file.mimetype)) {
            return cb(new Error('Invalid MIME type'));
        }

        cb(null, true);
    }
});

app.post('/upload', upload.single('image'), async (req, res) => {
    if (!req.file) {
        return res.status(400).send('No file uploaded');
    }

    // Additional MIME verification using file-type library
    const buffer = await fs.readFile(req.file.path);
    const type = await fileType.fromBuffer(buffer);

    if (!type || !['image/jpeg', 'image/png'].includes(type.mime)) {
        await fs.unlink(req.file.path);
        return res.status(400).send('Invalid file type');
    }

    res.send('File uploaded successfully');
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="JavaScript file upload with all 4 protections: extension check, MIME verification with file-type, size limit, and filename sanitization",
                tags=["javascript", "multer", "secure", "all_protections", "file-type"]
            ),

            DetectorValidationSample(
                name="javascript_filefilter_but_no_storage_sanitization",
                code='''const express = require('express');
const multer = require('multer');
const path = require('path');
const app = express();

const upload = multer({
    dest: 'uploads/',
    limits: { fileSize: 5 * 1024 * 1024 },
    fileFilter: (req, file, cb) => {
        const allowedExts = ['.pdf', '.doc'];
        const allowedMimes = ['application/pdf', 'application/msword'];

        const ext = path.extname(file.originalname).toLowerCase();
        // This sanitization is in the fileFilter but NOT in storage.filename
        const filename = file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_');

        if (allowedExts.includes(ext) && allowedMimes.includes(file.mimetype)) {
            cb(null, true);
        } else {
            cb(new Error('Invalid file'));
        }
    }
});

app.post('/upload', upload.single('doc'), (req, res) => {
    res.send('Success');
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(1, 2),
                description="JavaScript file upload missing filename sanitization in storage configuration (MEDIUM)",
                tags=["javascript", "multer", "missing_sanitization", "medium"]
            ),

            # =================================================================
            # PHP - VULNERABLE SAMPLES
            # =================================================================

            DetectorValidationSample(
                name="php_trusting_files_type",
                code='''<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_FILES['upload'])) {
        $file = $_FILES['upload'];

        // CRITICAL: Trusting client-provided MIME type
        if ($file['type'] === 'image/jpeg' || $file['type'] === 'image/png') {
            move_uploaded_file($file['tmp_name'], 'uploads/' . $file['name']);
            echo 'File uploaded';
        } else {
            echo 'Invalid file type';
        }
    }
}
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="PHP file upload trusting $_FILES['type'] (MIME spoofing vulnerability)",
                tags=["php", "mime_spoofing", "critical"]
            ),

            DetectorValidationSample(
                name="php_no_extension_check",
                code='''<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_FILES['upload'])) {
        $file = $_FILES['upload'];

        // No extension validation
        move_uploaded_file($file['tmp_name'], 'uploads/' . $file['name']);
        echo 'File uploaded';
    }
}
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="PHP file upload with no extension validation",
                tags=["php", "missing_extension_check"]
            ),

            DetectorValidationSample(
                name="php_dangerous_file_type",
                code='''<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_FILES['upload'])) {
        $file = $_FILES['upload'];
        $allowed_extensions = ['jpg', 'png', 'gif', 'php'];  // CRITICAL: Allowing PHP files

        $extension = pathinfo($file['name'], PATHINFO_EXTENSION);
        if (in_array(strtolower($extension), $allowed_extensions)) {
            move_uploaded_file($file['tmp_name'], 'uploads/' . $file['name']);
            echo 'File uploaded';
        } else {
            echo 'Invalid extension';
        }
    }
}
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_UPLOAD"],
                expected_score=(0, 2),
                description="PHP file upload allowing dangerous PHP file type (code execution risk)",
                tags=["php", "dangerous_file_type", "critical"]
            ),

            # =================================================================
            # PHP - SECURE SAMPLES
            # =================================================================

            DetectorValidationSample(
                name="php_all_protections",
                code='''<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_FILES['upload'])) {
        $file = $_FILES['upload'];
        $allowed_extensions = ['jpg', 'jpeg', 'png', 'gif'];
        $allowed_mimes = ['image/jpeg', 'image/png', 'image/gif'];
        $max_size = 10 * 1024 * 1024; // 10MB

        // Size limit check
        if ($file['size'] > $max_size) {
            die('File too large');
        }

        // Extension validation
        $extension = pathinfo($file['name'], PATHINFO_EXTENSION);
        if (!in_array(strtolower($extension), $allowed_extensions)) {
            die('Invalid extension');
        }

        // MIME type verification using finfo
        $finfo = finfo_open(FILEINFO_MIME_TYPE);
        $mime = finfo_file($finfo, $file['tmp_name']);
        finfo_close($finfo);

        if (!in_array($mime, $allowed_mimes)) {
            die('Invalid file type');
        }

        // Filename sanitization
        $safe_name = preg_replace('/[^a-zA-Z0-9._-]/', '_', $file['name']);
        $filename = time() . '_' . $safe_name;

        move_uploaded_file($file['tmp_name'], 'uploads/' . $filename);
        echo 'File uploaded successfully';
    }
}
?>
''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP file upload with all 4 protections: extension check, MIME verification with finfo, size limit, and filename sanitization",
                tags=["php", "secure", "all_protections", "finfo"]
            ),

            DetectorValidationSample(
                name="php_secure_wordpress_style",
                code='''<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (isset($_FILES['upload'])) {
        $file = $_FILES['upload'];
        $allowed_types = ['image/jpeg', 'image/png', 'application/pdf'];
        $max_size = 5 * 1024 * 1024;

        // Size check
        if ($file['size'] > $max_size) {
            die('File too large');
        }

        // Extension check
        $allowed_exts = ['jpg', 'jpeg', 'png', 'pdf'];
        $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
        if (!in_array($ext, $allowed_exts)) {
            die('Invalid extension');
        }

        // MIME verification
        $finfo = new finfo(FILEINFO_MIME_TYPE);
        $mime = $finfo->file($file['tmp_name']);
        if (!in_array($mime, $allowed_types)) {
            die('Invalid MIME type');
        }

        // Sanitize filename
        $filename = sanitize_file_name($file['name']);
        move_uploaded_file($file['tmp_name'], 'uploads/' . $filename);
        echo 'Success';
    }
}

function sanitize_file_name($filename) {
    return preg_replace('/[^a-zA-Z0-9._-]/', '', $filename);
}
?>
''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="PHP secure file upload WordPress style",
                tags=["php", "secure", "wordpress"]
            ),

            # =================================================================
            # EDGE CASES
            # =================================================================

            DetectorValidationSample(
                name="no_file_upload_code",
                code='''def process_data(data):
    """Process some data without file upload."""
    result = data * 2
    return result
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Code with no file upload functionality",
                tags=["edge_case", "no_file_upload"]
            ),

            DetectorValidationSample(
                name="file_download_not_upload",
                code='''from flask import Flask, send_file

app = Flask(__name__)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(f'files/{filename}', as_attachment=True)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="File download functionality (not upload)",
                tags=["edge_case", "file_download"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run the validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFileUploadDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
