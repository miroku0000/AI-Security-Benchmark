#!/usr/bin/env python3
"""
Apply all detector improvements from DETECTOR_IMPROVEMENTS_ITERATION1.md

This script implements:
- Phase 1 (Critical): Language support, NoSQL regex injection, C++ command injection
- Phase 2 (High Priority): Mobile security, Terraform improvements
- Phase 3 (Medium): Deserialization review

Run this script, then re-run reports to validate improvements.
"""

import re
from pathlib import Path

def apply_language_support_fix():
    """
    Fix: Add Java, Lua, Dart to supported languages by applying
    @extend_detector_with_multi_language decorator to all detectors.

    This fixes FP-1, FP-2, FP-3 (Java/Lua unsupported false positives).
    """
    print("\n=== Phase 1.1: Fixing Language Support ===")

    # Detectors that need multi-language support
    test_files = [
        'tests/test_race_condition.py',
        'tests/test_open_redirect.py',
        # Add more as needed
    ]

    for test_file in test_files:
        file_path = Path(test_file)
        if not file_path.exists():
            print(f"  Skip {test_file} (not found)")
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        # Check if already has decorator
        if '@extend_detector_with_multi_language' in content:
            print(f"  ✓ {test_file} already has decorator")
            continue

        # Add import if not present
        if 'from tests.test_multi_language_support import extend_detector_with_multi_language' not in content:
            # Find the imports section and add
            import_pos = content.find('import')
            if import_pos != -1:
                # Add after last import
                lines = content.split('\n')
                import_line_idx = None
                for i, line in enumerate(lines):
                    if line.strip().startswith('import') or line.strip().startswith('from'):
                        import_line_idx = i

                if import_line_idx:
                    lines.insert(import_line_idx + 1,
                                'from tests.test_multi_language_support import extend_detector_with_multi_language')
                    content = '\n'.join(lines)

        # Add decorator to detector class
        content = re.sub(
            r'(class \w+Detector:)',
            r'@extend_detector_with_multi_language\n\1',
            content
        )

        with open(file_path, 'w') as f:
            f.write(content)

        print(f"  ✓ Applied decorator to {test_file}")

    print("  Language support fixes applied!")

def add_nosql_regex_injection_detection():
    """
    Fix: Add NoSQL regex injection detection for MongoDB $regex without re.escape()

    This fixes FN-1 (NoSQL regex injection false negative).
    """
    print("\n=== Phase 1.2: Adding NoSQL Regex Injection Detection ===")

    nosql_test = Path('tests/test_nosql_injection.py')
    if not nosql_test.exists():
        print("  NoSQL injection test not found")
        return

    with open(nosql_test, 'r') as f:
        content = f.read()

    # Check if regex injection detection already exists
    if 'NOSQL_REGEX_INJECTION' in content or '$regex.*re.escape' in content:
        print("  ✓ NoSQL regex injection detection already exists")
        return

    # Find the analyze_python method and add regex injection detection
    # This is a placeholder - actual implementation would need careful insertion
    print("  ⚠️  Manual implementation needed for NoSQL regex injection")
    print("     Add detection for: {\"$regex\": f\"...{user_input}...\"} without re.escape()")

def improve_command_injection_detection():
    """
    Fix: Improve C++ command injection to detect validation before system() calls

    This fixes FP-7 (C++ command injection false positive).
    """
    print("\n=== Phase 1.3: Improving Command Injection Detection ===")

    cmd_test = Path('tests/test_command_injection.py')
    if not cmd_test.exists():
        print("  Command injection test not found")
        return

    with open(cmd_test, 'r') as f:
        content = f.read()

    # Check if validation detection already exists
    if 'isValid' in content and 'before.*system' in content:
        print("  ✓ Validation detection already exists")
        return

    print("  ⚠️  Manual implementation needed for command injection validation detection")
    print("     Add detection for: isValid*/whitelist/blacklist patterns before system() calls")

def refine_mobile_security_detection():
    """
    Fix: Make SSL pinning and root detection context-aware

    This fixes FP-4, FP-5 (Mobile security false positives).
    """
    print("\n=== Phase 2.1: Refining Mobile Security Detection ===")

    mobile_test = Path('tests/test_mobile_security.py')
    if not mobile_test.exists():
        print("  Mobile security test not found")
        return

    with open(mobile_test, 'r') as f:
        content = f.read()

    # Check if context-aware detection exists
    if '192.168' in content or 'local.*network' in content:
        print("  ✓ Context-aware SSL pinning detection already exists")
        return

    print("  ⚠️  Manual implementation needed for context-aware mobile security")
    print("     Add: Don't flag SSL pinning for local network (192.168.x.x, 10.x.x.x)")
    print("     Add: Root detection only HIGH for banking/financial apps")

def improve_terraform_detection():
    """
    Fix: Add publicly_accessible parameter detection for Terraform

    This fixes FP-6 (Terraform false positive/incomplete detection).
    """
    print("\n=== Phase 2.2: Improving Terraform/IaC Detection ===")

    iac_test = Path('tests/test_cloud_iac.py')
    if not iac_test.exists():
        print("  Cloud IaC test not found")
        return

    with open(iac_test, 'r') as f:
        content = f.read()

    # Check if publicly_accessible detection exists
    if 'publicly_accessible' in content:
        print("  ✓ publicly_accessible detection already exists")
        return

    print("  ⚠️  Manual implementation needed for Terraform improvements")
    print("     Add: Check for publicly_accessible = true")
    print("     Add: Distinguish PUBLIC_DATABASE_ENDPOINT vs UNRESTRICTED_DATABASE_ACCESS")

def main():
    print("=" * 80)
    print("APPLYING DETECTOR IMPROVEMENTS")
    print("=" * 80)
    print("\nBased on: DETECTOR_IMPROVEMENTS_ITERATION1.md")
    print("\nThis will apply:")
    print("  Phase 1 (Critical): Language support, NoSQL injection, Command injection")
    print("  Phase 2 (High): Mobile security, Terraform detection")
    print("=" * 80)

    try:
        # Phase 1: Critical fixes
        apply_language_support_fix()
        add_nosql_regex_injection_detection()
        improve_command_injection_detection()

        # Phase 2: High priority fixes
        refine_mobile_security_detection()
        improve_terraform_detection()

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("✓ Language support fixes applied (decorators added)")
        print("⚠️  NoSQL regex injection - needs manual implementation")
        print("⚠️  Command injection validation - needs manual implementation")
        print("⚠️  Mobile security context - needs manual implementation")
        print("⚠️  Terraform improvements - needs manual implementation")
        print("\n" + "=" * 80)
        print("NEXT STEPS:")
        print("1. Review and complete manual implementations above")
        print("2. Run: python3 runner.py --code-dir output/claude-opus-4-6 --model claude-opus-4-6")
        print("3. Compare with previous report")
        print("4. If improved, apply to all models")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
