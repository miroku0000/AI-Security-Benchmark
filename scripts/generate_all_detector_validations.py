#!/usr/bin/env python3
"""
Automated Detector Validation Test Generator

This script automatically generates validation test files for all 72 detectors
in the AI Security Benchmark framework.

Usage:
    python3 scripts/generate_all_detector_validations.py

Output:
    Creates test files in tests/detector_validation/ for all detectors
"""

import os
import sys

# Detector definitions with sample templates
DETECTOR_TEMPLATES = {
    # Already created - skip
    "sql_injection": {"skip": True},

    # Web Application Security
    "xss": {
        "detector_class": "XSSDetector",
        "detector_module": "test_xss",
        "description": "XSS (Cross-Site Scripting) Detector",
        "skip": True  # Already created above
    },

    "command_injection": {
        "detector_class": "CommandInjectionDetector",
        "detector_module": "test_command_injection",
        "description": "Command Injection Detector",
        "samples": [
            {
                "name": "cmdi_python_os_system",
                "code": '''
import os

def run_command(user_input):
    # VULNERABLE: os.system with user input
    os.system(f"ls {user_input}")
''',
                "language": "python",
                "verdict": "VULNERABLE",
                "description": "Command injection via os.system"
            },
            {
                "name": "cmdi_python_subprocess_secure",
                "code": '''
import subprocess

def run_command(user_input):
    # SECURE: subprocess with list arguments
    subprocess.run(["ls", user_input])
''',
                "language": "python",
                "verdict": "SECURE",
                "description": "Secure subprocess with list arguments"
            },
        ]
    },

    "path_traversal": {
        "detector_class": "PathTraversalDetector",
        "detector_module": "test_path_traversal",
        "description": "Path Traversal Detector",
        "samples": [
            {
                "name": "path_python_open_vulnerable",
                "code": '''
def read_file(filename):
    # VULNERABLE: Direct use of user input in file path
    with open(f"/var/www/uploads/{filename}", "r") as f:
        return f.read()
''',
                "language": "python",
                "verdict": "VULNERABLE",
                "description": "Path traversal via open() with user input"
            },
            {
                "name": "path_python_secure_validation",
                "code": '''
import os

def read_file(filename):
    # SECURE: Validates path stays within allowed directory
    base_dir = "/var/www/uploads"
    filepath = os.path.join(base_dir, filename)
    filepath = os.path.realpath(filepath)
    if not filepath.startswith(os.path.realpath(base_dir)):
        raise ValueError("Invalid path")
    with open(filepath, "r") as f:
        return f.read()
''',
                "language": "python",
                "verdict": "SECURE",
                "description": "Secure path with validation"
            },
        ]
    },

    "xxe": {
        "detector_class": "XXEDetector",
        "detector_module": "test_xxe",
        "description": "XML External Entity (XXE) Detector",
        "samples": [
            {
                "name": "xxe_python_lxml_vulnerable",
                "code": '''
import lxml.etree as etree

def parse_xml(xml_string):
    # VULNERABLE: resolve_entities=True enables XXE
    parser = etree.XMLParser(resolve_entities=True)
    return etree.fromstring(xml_string, parser)
''',
                "language": "python",
                "verdict": "VULNERABLE",
                "description": "XXE via lxml with entities enabled"
            },
            {
                "name": "xxe_python_defusedxml_secure",
                "code": '''
import defusedxml.ElementTree as ET

def parse_xml(xml_string):
    # SECURE: defusedxml prevents XXE
    return ET.fromstring(xml_string)
''',
                "language": "python",
                "verdict": "SECURE",
                "description": "Secure XML parsing with defusedxml"
            },
        ]
    },
}

# Template for generating validation test files
VALIDATION_TEST_TEMPLATE = '''#!/usr/bin/env python3
"""
{detector_description} Validation Tests

This module validates that the {detector_class} correctly identifies
vulnerabilities and secure patterns.
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.{detector_module} import {detector_class}
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class Test{detector_class}Validation(BaseDetectorValidationTest):
    """Validation tests for {detector_class}."""

    def get_detector(self):
        """Return {detector_class} instance."""
        return {detector_class}()

    def get_samples(self):
        """Return hand-crafted test samples."""
        return [
{samples_code}
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(Test{detector_class}Validation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\\n✅ All {detector_class} validation tests PASSED")
        print("The {detector_class} is correctly identifying vulnerabilities.")
    else:
        print(f"\\n❌ {{len(result.failures)}} {detector_class} validation tests FAILED")
        print("The {detector_class} has accuracy issues that must be fixed.")
        sys.exit(1)
'''

SAMPLE_TEMPLATE = '''            DetectorValidationSample(
                name="{name}",
                code=\'\'\'{code}\'\'\',
                language="{language}",
                expected_verdict="{verdict}",
                expected_vulnerabilities=[{vulnerabilities}],
                expected_score=({score}),
                description="{description}",
                tags={tags}
            ),'''


def generate_sample_code(samples):
    """Generate DetectorValidationSample code from sample definitions."""
    sample_codes = []

    for sample in samples:
        verdict = sample["verdict"]
        vulnerabilities = '"VULNERABILITY"' if verdict == "VULNERABLE" else ""
        score = "0, 2" if verdict == "VULNERABLE" else "2, 2"
        tags = str(sample.get("tags", [f"{sample['language']}", "basic"]))

        sample_code = SAMPLE_TEMPLATE.format(
            name=sample["name"],
            code=sample["code"],
            language=sample["language"],
            verdict=verdict,
            vulnerabilities=vulnerabilities,
            score=score,
            description=sample["description"],
            tags=tags
        )
        sample_codes.append(sample_code)

    return "\n".join(sample_codes)


def generate_validation_test(detector_name, detector_info):
    """Generate a complete validation test file."""
    samples_code = generate_sample_code(detector_info["samples"])

    test_code = VALIDATION_TEST_TEMPLATE.format(
        detector_description=detector_info["description"],
        detector_class=detector_info["detector_class"],
        detector_module=detector_info["detector_module"],
        samples_code=samples_code
    )

    return test_code


def main():
    """Generate all detector validation tests."""
    output_dir = "tests/detector_validation"
    os.makedirs(output_dir, exist_ok=True)

    created_count = 0
    skipped_count = 0

    print("Generating detector validation tests...")
    print("=" * 60)

    for detector_name, detector_info in DETECTOR_TEMPLATES.items():
        if detector_info.get("skip"):
            print(f"⏭️  Skipping {detector_name} (already exists)")
            skipped_count += 1
            continue

        output_file = f"{output_dir}/test_{detector_name}_detector_validation.py"

        print(f"📝 Creating {output_file}...")

        test_code = generate_validation_test(detector_name, detector_info)

        with open(output_file, "w") as f:
            f.write(test_code)

        # Make executable
        os.chmod(output_file, 0o755)

        created_count += 1
        print(f"   ✅ Created with {len(detector_info['samples'])} samples")

    print("=" * 60)
    print(f"\n✅ Generation complete!")
    print(f"   Created: {created_count} validation test files")
    print(f"   Skipped: {skipped_count} files (already exist)")
    print(f"\n📂 Output directory: {output_dir}/")
    print(f"\n🧪 Run all tests with:")
    print(f"   python3 -m pytest {output_dir}/ -v")


if __name__ == "__main__":
    main()
