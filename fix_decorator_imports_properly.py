#!/usr/bin/env python3
"""
Fix the decorator imports by moving them to the top of the file.
"""
import re
from pathlib import Path

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

def fix_import_in_file(file_path):
    """Fix the import statement location in a detector file."""
    path = Path(file_path)
    if not path.exists():
        print(f"  ⚠️  File not found: {file_path}")
        return False

    with open(path, 'r') as f:
        content = f.read()

    # Remove any existing imports of extend_detector_with_multi_language (they might be in wrong place)
    content = re.sub(r'from tests\.test_multi_language_support import extend_detector_with_multi_language\n?', '', content)

    # Find the first non-import, non-comment, non-docstring line after imports
    lines = content.split('\n')
    insert_idx = 0

    in_docstring = False
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track docstrings
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if in_docstring:
                in_docstring = False
                continue
            else:
                in_docstring = True
                continue

        if in_docstring:
            continue

        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            continue

        # If it's an import line, update insert_idx
        if stripped.startswith('import ') or stripped.startswith('from '):
            insert_idx = i
        else:
            # Found first non-import line
            break

    # Insert the import after the last import, with a blank line before it
    if insert_idx > 0:
        lines.insert(insert_idx + 1, 'from tests.test_multi_language_support import extend_detector_with_multi_language')
        content = '\n'.join(lines)

    # Write back
    with open(path, 'w') as f:
        f.write(content)

    print(f"  ✓ Fixed import in {file_path}")
    return True

def main():
    print("=" * 80)
    print("FIXING DECORATOR IMPORTS")
    print("=" * 80)
    print(f"\nProcessing {len(DETECTOR_FILES)} detector files...")
    print()

    success_count = 0
    for file_path in DETECTOR_FILES:
        if fix_import_in_file(file_path):
            success_count += 1

    print()
    print("=" * 80)
    print(f"COMPLETED: {success_count}/{len(DETECTOR_FILES)} files processed")
    print("=" * 80)

if __name__ == '__main__':
    main()
