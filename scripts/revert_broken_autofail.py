#!/usr/bin/env python3
"""
Revert Broken Auto-Fail Code

Removes the buggy auto-fail code that was incorrectly added by the add_critical_autofail.py script.
The code was added in the wrong places and references non-existent instance variables.
"""
import re
from pathlib import Path

def clean_autofail_code(content):
    """Remove buggy auto-fail code blocks."""

    # Pattern 1: Remove standalone auto-fail blocks that reference self.vulnerabilities or self.score
    # These are the buggy blocks added by the script
    pattern1 = r'\n\s*# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0\s*\n\s*if any\(v\.get\(["\']severity["\']\) == ["\']CRITICAL["\'] for v in self\.vulnerabilities\):\s*\n\s*final_score = 0\s*\n\s*if self\.score > 0:\s*\n\s*self\.score = 0\s*\n'

    content = re.sub(pattern1, '\n', content)

    # Pattern 2: Remove duplicate auto-fail blocks with local vulnerabilities variable
    # But keep one if it's properly placed
    pattern2 = r'\n\s*#\s*Auto-fail for CRITICAL vulnerabilities\s*\n+\s*if any\(v\.get\("severity"\) == "CRITICAL" for v in vulnerabilities\):\s*\n+\s*score = 0\s*\n+'

    # Count occurrences
    matches = list(re.finditer(pattern2, content))
    if len(matches) > 1:
        # Keep the last one (most likely to be in the right place), remove others
        for match in matches[:-1]:
            content = content[:match.start()] + '\n' + content[match.end():]

    return content

def process_file(file_path):
    """Process a single detector file to remove buggy auto-fail code."""
    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content
    content = clean_autofail_code(content)

    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    tests_dir = Path("tests")
    detector_files = list(tests_dir.glob("test_*.py"))

    print("=" * 80)
    print("REVERTING BROKEN AUTO-FAIL CODE")
    print("=" * 80)
    print(f"\nProcessing {len(detector_files)} detector files...\n")

    fixed_count = 0
    for detector_file in sorted(detector_files):
        print(f"  {detector_file.name}...", end=" ")
        if process_file(detector_file):
            fixed_count += 1
            print("✓ Cleaned")
        else:
            print("- No broken code found")

    print(f"\n{'=' * 80}")
    print(f"SUMMARY: Cleaned {fixed_count} / {len(detector_files)} files")
    print(f"{'=' * 80}\n")

if __name__ == "__main__":
    main()
