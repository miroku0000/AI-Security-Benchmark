#!/usr/bin/env python3
"""
Add CRITICAL Auto-Fail to test_multi_language_support.py

This file has 41 return statements with the pattern:
    return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}

We need to add auto-fail before each return.
"""
import re
import ast

def add_autofail_multi_language():
    filepath = "tests/test_multi_language_support.py"

    with open(filepath, 'r') as f:
        content = f.read()

    # Check if already has auto-fail
    if '# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0' in content:
        print("File already has auto-fail logic")
        return False

    # Pattern: return {"score": score, "vulnerabilities": vulnerabilities, "max_score": 2}
    # We want to insert auto-fail BEFORE this return

    pattern = r'(\n)([ \t]+)(return \{"score": score, "vulnerabilities": vulnerabilities, "max_score": 2\})'

    def replace_func(match):
        newline = match.group(1)
        indent = match.group(2)
        return_stmt = match.group(3)

        autofail = (
            f"{newline}{indent}# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0\n"
            f"{indent}if any(v.get('severity') == 'CRITICAL' for v in vulnerabilities):\n"
            f"{indent}    score = 0\n"
            f"{newline}{indent}{return_stmt}"
        )
        return autofail

    modified = re.sub(pattern, replace_func, content)

    # Validate syntax
    try:
        ast.parse(modified)
    except SyntaxError as e:
        print(f"Syntax error: {e}")
        return False

    # Count replacements
    count = modified.count('# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0')

    if count == 0:
        print("No replacements made - pattern not found")
        return False

    # Write file
    with open(filepath, 'w') as f:
        f.write(modified)

    print(f"✓ Modified test_multi_language_support.py ({count} return statements)")
    return True

if __name__ == "__main__":
    success = add_autofail_multi_language()
    exit(0 if success else 1)
