#!/usr/bin/env python3
"""
Fix missing decorator imports in all detector files.
"""
import re
from pathlib import Path

# Find all Python files in tests/ that use the decorator
tests_dir = Path("tests")
decorator_line = "@extend_detector_with_multi_language"
import_line = "from tests.test_multi_language_support import extend_detector_with_multi_language\n"

files_fixed = 0
files_skipped = 0

for py_file in tests_dir.glob("*.py"):
    # Skip the file that defines the decorator
    if py_file.name == "test_multi_language_support.py":
        continue

    # Read the file
    content = py_file.read_text()

    # Check if it uses the decorator
    if decorator_line not in content:
        continue

    # Check if it already has the import
    if "from tests.test_multi_language_support import extend_detector_with_multi_language" in content:
        print(f"○ {py_file.name} already has the import")
        files_skipped += 1
        continue

    # Find the last import line
    lines = content.split('\n')
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('from ') or line.startswith('import '):
            last_import_idx = i

    if last_import_idx >= 0:
        # Insert the import after the last import line
        lines.insert(last_import_idx + 1, import_line.rstrip())

        # Write back
        new_content = '\n'.join(lines)
        py_file.write_text(new_content)

        print(f"✓ Fixed {py_file.name}")
        files_fixed += 1
    else:
        print(f"✗ Could not find imports in {py_file.name}")

print()
print(f"Summary: Fixed {files_fixed} files, Skipped {files_skipped} files")
