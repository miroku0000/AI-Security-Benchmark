#!/usr/bin/env python3
"""
Fix detectors that return "Unsupported language" by removing language checks
from analyze() methods and letting the multi-language decorator handle it.
"""
import re
from pathlib import Path


def fix_detector_file(file_path: Path):
    """Fix a single detector file by removing unsupported language returns."""
    with open(file_path, 'r') as f:
        content = f.read()

    original = content
    changes = []

    # Pattern 1: Simple unsupported language return in analyze()
    # return {"score": 0, "vulnerabilities": ["Unsupported language"], "max_score": 2}
    pattern1 = r'return\s+\{\s*"score"\s*:\s*0\s*,\s*"vulnerabilities"\s*:\s*\["Unsupported language"\]\s*,?\s*("max_score"\s*:\s*2\s*)?\}'
    if re.search(pattern1, content):
        changes.append("Removed simple 'Unsupported language' return")
        # Don't remove it yet, we need to handle the else block

    # Pattern 2: if/elif/else chains that end with unsupported language
    # We need to remove the final else block that returns unsupported language
    # BUT only if it's in the analyze() method

    # Find the analyze() method
    analyze_match = re.search(r'def analyze\(self,.*?\).*?:\s*\n(.*?)(?=\n    def |\nclass |\Z)', content, re.DOTALL)

    if analyze_match:
        analyze_body = analyze_match.group(1)
        analyze_start = analyze_match.start(1)
        analyze_end = analyze_match.end(1)

        # Check if it has an else block with unsupported language
        else_pattern = r'(\s+)else:\s*\n\1    return\s+\{\s*["\']score["\']\s*:\s*[02]\s*,\s*["\']vulnerabilities["\']\s*:\s*\[["\']Unsupported language["\']\].*?\}'

        else_matches = list(re.finditer(else_pattern, analyze_body, re.DOTALL))

        if else_matches:
            # Remove the last else block (the unsupported language one)
            last_else = else_matches[-1]

            # Also need to remove the preceding elif if it becomes dangling
            # Find the full if/elif chain
            lines_before_else = analyze_body[:last_else.start()].split('\n')

            # Check if the line before else is an elif
            for i in range(len(lines_before_else) - 1, -1, -1):
                line = lines_before_else[i].strip()
                if line and not line.startswith('#'):
                    # Found the last non-empty, non-comment line
                    break

            # Remove the else block from the analyze body
            new_analyze_body = analyze_body[:last_else.start()] + analyze_body[last_else.end():]

            # Reconstruct the content
            content = content[:analyze_start] + new_analyze_body + content[analyze_end:]
            changes.append(f"Removed unsupported language else block from analyze()")

    if content != original:
        # Save the changes
        with open(file_path, 'w') as f:
            f.write(content)
        return True, changes

    return False, []


def main():
    tests_dir = Path('tests')

    # List of files to fix (from grep results)
    files_to_fix = [
        'test_xss.py',
        'test_command_injection.py',
        'test_secrets.py',
        'test_sql_injection.py',
        'test_mobile_security.py',
        'test_oidc.py',
        'test_business_logic.py',
        'test_ssrf.py',
        'test_file_upload.py',
        'test_path_traversal.py',
        'test_deserialization.py',
        'test_csrf.py',
        'test_access_control.py',
        'test_error_handling.py',
        'test_race_condition.py',
        'test_ldap_injection.py',
        'test_xxe.py',
        'test_observability.py',
        'test_supply_chain.py',
        'test_soap.py',
        'test_message_queue.py',
        'test_saml.py',
        'test_rate_limiting.py',
        'test_supply_chain_security.py',
        'test_sensitive_logging.py',
        'test_resource_leaks.py',
        'test_open_redirect.py',
        'test_nosql_injection.py',
        'test_missing_authz.py',
        'test_missing_auth.py',
        'test_jwt.py',
        'test_insecure_auth.py',
        'test_input_validation.py',
        'test_info_disclosure.py',
        'test_code_injection.py',
    ]

    fixed_count = 0
    for filename in files_to_fix:
        file_path = tests_dir / filename
        if not file_path.exists():
            print(f"⚠️  {filename}: File not found")
            continue

        was_fixed, changes = fix_detector_file(file_path)
        if was_fixed:
            fixed_count += 1
            print(f"✅ {filename}: Fixed")
            for change in changes:
                print(f"   - {change}")
        else:
            print(f"ℹ️  {filename}: No changes needed (or couldn't auto-fix)")

    print(f"\nFixed {fixed_count}/{len(files_to_fix)} files")
    print("\nNote: Some files may require manual review if the pattern wasn't detected.")


if __name__ == '__main__':
    main()
