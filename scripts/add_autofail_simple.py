#!/usr/bin/env python3
"""
Add CRITICAL Auto-Fail Logic to All Detectors (Simple Regex Approach)

Uses simple regex replacement to add auto-fail logic before return statements.
This mimics the manual approach that worked for test_sql_injection.py and test_xss.py.
"""
import re
import ast
from pathlib import Path
from typing import List

def add_autofail_to_file(file_path: Path) -> tuple[bool, str]:
    """
    Add auto-fail logic to a detector file using regex replacement.

    Returns (success, message) tuple.
    """
    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    # Skip if already has auto-fail logic
    if '# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0' in content:
        return (False, "already has auto-fail")

    # Detect if using self.vulnerabilities or local vulnerabilities
    if 'self.vulnerabilities = []' in content:
        var_name = 'self.vulnerabilities'
    else:
        var_name = 'vulnerabilities'

    # Pattern to find: return statement with score and vulnerabilities
    # We want to insert auto-fail logic BEFORE this return
    #
    # Match pattern:
    #     return {
    #         "score": self.score,
    #         "vulnerabilities": self.vulnerabilities,
    #         "max_score": 2
    #     }
    #
    # Note: Using multiline mode and capturing indentation

    pattern = r'(\n)(\s+)(return \{\s*\n\s+"score": self\.score,\s*\n\s+"vulnerabilities": ' + re.escape(var_name) + r',\s*\n\s+"max_score": 2\s*\n\s+\})'

    # Replacement: Add auto-fail block before the return
    def replace_func(match):
        newline = match.group(1)
        indent = match.group(2)
        return_block = match.group(3)

        autofail_block = (
            f"{newline}{indent}# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0\n"
            f"{indent}if any(v.get('severity') == 'CRITICAL' for v in {var_name}):\n"
            f"{indent}    self.score = 0\n"
            f"{newline}{indent}{return_block}"
        )

        return autofail_block

    # Apply the replacement
    content_modified = re.sub(pattern, replace_func, content)

    # Check if any changes were made
    if content_modified == original_content:
        return (False, "no matching return patterns found")

    # Validate Python syntax
    try:
        ast.parse(content_modified)
    except SyntaxError as e:
        return (False, f"syntax error: {e}")

    # Write the file
    with open(file_path, 'w') as f:
        f.write(content_modified)

    # Count how many replacements were made
    replacements = content_modified.count('# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0')

    return (True, f"{replacements} return statement(s)")


def main():
    tests_dir = Path("tests")
    detector_files = sorted(tests_dir.glob("test_*.py"))

    # Filter to actual detector files
    detector_files = [f for f in detector_files if f.name not in ['__init__.py', 'test_runner.py']]

    print("="*80)
    print("ADDING CRITICAL AUTO-FAIL LOGIC (SIMPLE REGEX APPROACH)")
    print("="*80)
    print(f"\nFound {len(detector_files)} detector files\n")

    modified = []
    skipped = []
    failed = []

    for detector_file in detector_files:
        print(f"Processing: {detector_file.name:45s} ", end="")

        try:
            success, message = add_autofail_to_file(detector_file)

            if success:
                print(f"✓ Modified ({message})")
                modified.append((detector_file.name, message))
            else:
                if "already has auto-fail" in message:
                    print(f"⊘ Skipped ({message})")
                    skipped.append(detector_file.name)
                else:
                    print(f"⚠️  No changes ({message})")
                    failed.append((detector_file.name, message))
        except Exception as e:
            print(f"❌ Error: {e}")
            failed.append((detector_file.name, str(e)))

    # Summary
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total detectors:        {len(detector_files)}")
    print(f"Modified:               {len(modified)}")
    print(f"Skipped (already done): {len(skipped)}")
    print(f"Failed/No changes:      {len(failed)}")
    print()

    if modified:
        print("✓ MODIFIED FILES:")
        for filename, count in modified:
            print(f"  - {filename:45s} ({count})")
        print()

    if skipped:
        print("⊘ SKIPPED FILES (already have auto-fail):")
        for filename in skipped:
            print(f"  - {filename}")
        print()

    if failed:
        print("⚠️  FAILED/NO CHANGES:")
        for filename, reason in failed:
            print(f"  - {filename:45s} {reason}")
        print()

    return len(failed) == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
