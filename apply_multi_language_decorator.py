#!/usr/bin/env python3
"""
Script to add multi-language decorator to all detector files.
"""
import re
from pathlib import Path

# List of all detector files that need the decorator
DETECTOR_FILES = [
    'tests/test_access_control.py',
    'tests/test_business_logic.py',
    'tests/test_code_injection.py',
    'tests/test_command_injection.py',
    'tests/test_csrf.py',
    'tests/test_deserialization.py',
    'tests/test_error_handling.py',
    'tests/test_file_upload.py',
    'tests/test_info_disclosure.py',
    'tests/test_input_validation.py',
    'tests/test_insecure_auth.py',
    'tests/test_jwt.py',
    'tests/test_ldap_injection.py',
    'tests/test_missing_auth.py',
    'tests/test_missing_authz.py',
    'tests/test_mobile_security.py',
    'tests/test_nosql_injection.py',
    'tests/test_open_redirect.py',
    'tests/test_path_traversal.py',
    'tests/test_race_condition.py',
    'tests/test_rate_limiting.py',
    'tests/test_resource_leaks.py',
    'tests/test_secrets.py',
    'tests/test_sensitive_logging.py',
    'tests/test_sql_injection.py',
    'tests/test_ssrf.py',
    'tests/test_supply_chain_security.py',
    'tests/test_xss.py',
    'tests/test_xxe.py',
]

def add_decorator_to_file(file_path):
    """Add multi-language decorator to a single detector file."""
    path = Path(file_path)
    if not path.exists():
        print(f"  ⚠️  File not found: {file_path}")
        return False

    with open(path, 'r') as f:
        content = f.read()

    # Check if already has decorator
    if '@extend_detector_with_multi_language' in content:
        print(f"  ✓ {file_path} already has decorator")
        return True

    # Check if already has import
    has_import = 'from tests.test_multi_language_support import extend_detector_with_multi_language' in content

    # Add import if not present
    if not has_import:
        # Find the last import line
        lines = content.split('\n')
        last_import_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                last_import_idx = i

        # Insert the import after the last import
        if last_import_idx > 0:
            lines.insert(last_import_idx + 1, 'from tests.test_multi_language_support import extend_detector_with_multi_language')
            content = '\n'.join(lines)

    # Add decorator before class definition
    # Find all class definitions that look like detector classes
    content = re.sub(
        r'(\n)(class \w+Detector[:\(])',
        r'\1@extend_detector_with_multi_language\n\2',
        content
    )

    # Write back
    with open(path, 'w') as f:
        f.write(content)

    print(f"  ✓ Applied decorator to {file_path}")
    return True

def main():
    print("=" * 80)
    print("APPLYING MULTI-LANGUAGE DECORATOR TO ALL DETECTOR FILES")
    print("=" * 80)
    print(f"\nProcessing {len(DETECTOR_FILES)} detector files...")
    print()

    success_count = 0
    for file_path in DETECTOR_FILES:
        if add_decorator_to_file(file_path):
            success_count += 1

    print()
    print("=" * 80)
    print(f"COMPLETED: {success_count}/{len(DETECTOR_FILES)} files processed")
    print("=" * 80)

if __name__ == '__main__':
    main()
