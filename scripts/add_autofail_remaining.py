#!/usr/bin/env python3
"""
Add CRITICAL Auto-Fail to Remaining 9 Detectors

Handles detectors with different return patterns:
- Single quotes ('score' instead of "score")
- Different variable names (final_score instead of self.score)
- Different return formats
"""
import re
import ast
from pathlib import Path

def add_autofail_variant1(content: str, var_name: str) -> str:
    """Handle single-quote pattern with local variables."""
    # Pattern for single quotes, any score variable name
    pattern = r"(\n)(\s+)(return \{\s*\n\s+'score': (?:score|self\.score|final_score),\s*\n\s+'max_score': 2,\s*\n\s+'vulnerabilities': " + re.escape(var_name) + r"\s*\n\s+\})"

    def replace_func(match):
        newline = match.group(1)
        indent = match.group(2)
        return_block = match.group(3)

        autofail = (
            f"{newline}{indent}# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0\n"
            f"{indent}if any(v.get('severity') == 'CRITICAL' for v in {var_name}):\n"
            f"{indent}    self.score = 0\n"
            f"{newline}{indent}{return_block}"
        )
        return autofail

    return re.sub(pattern, replace_func, content)

def add_autofail_variant2(content: str, var_name: str) -> str:
    """Handle double-quote pattern with final_score variable."""
    # Pattern for final_score variable
    pattern = r'(\n)(\s+)(return \{\s*\n\s+"score": final_score,\s*\n\s+"vulnerabilities": ' + re.escape(var_name) + r',\s*\n\s+"max_score": 2\s*\n\s+\})'

    def replace_func(match):
        newline = match.group(1)
        indent = match.group(2)
        return_block = match.group(3)

        autofail = (
            f"{newline}{indent}# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0\n"
            f"{indent}if any(v.get('severity') == 'CRITICAL' for v in {var_name}):\n"
            f"{indent}    self.score = 0\n"
            f"{newline}{indent}{return_block}"
        )
        return autofail

    return re.sub(pattern, replace_func, content)

def process_file(filepath: Path) -> tuple[bool, str]:
    """Process a single file with all variants."""
    with open(filepath, 'r') as f:
        content = f.read()

    original = content

    # Skip if already has auto-fail
    if '# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0' in content:
        return (False, "already has auto-fail")

    # Detect variable style
    if 'self.vulnerabilities = []' in content:
        var_name = 'self.vulnerabilities'
    else:
        var_name = 'vulnerabilities'

    # Try variant 1 (single quotes)
    content = add_autofail_variant1(content, var_name)

    # Try variant 2 (final_score)
    content = add_autofail_variant2(content, var_name)

    if content == original:
        return (False, "no matching patterns")

    # Validate syntax
    try:
        ast.parse(content)
    except SyntaxError as e:
        return (False, f"syntax error: {e}")

    # Write file
    with open(filepath, 'w') as f:
        f.write(content)

    count = content.count('# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0')
    return (True, f"{count} return statement(s)")

def main():
    remaining_files = [
        "test_api_response_cache.py",
        "test_cicd_security.py",
        "test_container_security.py",
        "test_datastore_security.py",
        "test_graphql_security.py",
        "test_mass_assignment.py",
        "test_multi_language_support.py",
        "test_serverless_security.py",
        "test_universal_fallback.py"
    ]

    print("="*80)
    print("ADDING AUTO-FAIL TO REMAINING 9 DETECTORS")
    print("="*80)
    print()

    modified = []
    failed = []

    for filename in remaining_files:
        filepath = Path(f"tests/{filename}")
        print(f"Processing: {filename:45s} ", end="")

        try:
            success, message = process_file(filepath)
            if success:
                print(f"✓ Modified ({message})")
                modified.append((filename, message))
            else:
                print(f"⚠️  {message}")
                failed.append((filename, message))
        except Exception as e:
            print(f"❌ Error: {e}")
            failed.append((filename, str(e)))

    print()
    print("="*80)
    print(f"Modified: {len(modified)}/9")
    print(f"Failed:   {len(failed)}/9")
    print("="*80)

    if modified:
        print("\n✓ MODIFIED:")
        for name, msg in modified:
            print(f"  - {name:45s} ({msg})")

    if failed:
        print("\n⚠️  FAILED:")
        for name, msg in failed:
            print(f"  - {name:45s} {msg}")

    return len(failed) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
