#!/usr/bin/env python3
"""
Add CRITICAL Auto-Fail Logic to All Detectors

Automatically adds the following logic before return statements in all _analyze_* methods:

    # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
    if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
        self.score = 0

This ensures SECURE findings cannot mask CRITICAL vulnerabilities.
"""
import re
import ast
from pathlib import Path
from typing import List, Tuple

class AutoFailAdder:
    def __init__(self, tests_dir: Path = Path("tests")):
        self.tests_dir = tests_dir
        self.modified_files = []
        self.failed_files = []
        self.skipped_files = []

    def find_detector_files(self) -> List[Path]:
        """Find all detector test files."""
        detector_files = []
        for test_file in sorted(self.tests_dir.glob("test_*.py")):
            # Skip non-detector files
            if test_file.name in ['__init__.py', 'test_runner.py']:
                continue

            with open(test_file, 'r') as f:
                content = f.read()

            # Check if file contains detector class and analyze method
            if 'Detector' in content and 'def analyze' in content:
                detector_files.append(test_file)

        return detector_files

    def detect_variable_style(self, content: str) -> str:
        """Detect if detector uses self.vulnerabilities or local vulnerabilities."""
        if 'self.vulnerabilities = []' in content:
            return 'self.vulnerabilities'
        elif re.search(r'vulnerabilities\s*=\s*\[\]', content):
            return 'vulnerabilities'
        else:
            # Default to self.vulnerabilities
            return 'self.vulnerabilities'

    def has_autofail_already(self, content: str) -> bool:
        """Check if auto-fail logic already exists."""
        return '# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0' in content

    def find_return_statements_in_analyze_methods(self, content: str, var_style: str) -> List[Tuple[int, str]]:
        """
        Find return statements in _analyze_* methods that need auto-fail logic.

        Returns list of (line_number, indentation) tuples.
        """
        lines = content.split('\n')
        return_positions = []

        in_analyze_method = False
        current_method_indent = 0

        for i, line in enumerate(lines):
            # Check if entering an _analyze method
            if re.match(r'\s*def _analyze_\w+\(self', line):
                in_analyze_method = True
                current_method_indent = len(line) - len(line.lstrip())
                continue

            # Check if exiting the method (next method or class-level code)
            if in_analyze_method and line.strip() and not line.strip().startswith('#'):
                line_indent = len(line) - len(line.lstrip())
                if line_indent <= current_method_indent and line.strip():
                    # Check if it's a new method or end of class
                    if re.match(r'\s*def\s+', line) or re.match(r'\s*class\s+', line):
                        in_analyze_method = False

            # Look for return statements in analyze methods
            if in_analyze_method and re.match(r'\s*return\s*\{', line):
                # Check if this return uses the detected variable style
                # Look ahead to see if this is the final return with score/vulnerabilities
                context_start = max(0, i - 2)
                context_end = min(len(lines), i + 5)
                context = '\n'.join(lines[context_start:context_end])

                # Only modify returns that have score and vulnerabilities
                if '"score":' in context and '"vulnerabilities":' in context:
                    # Get indentation
                    indent = len(line) - len(line.lstrip())
                    return_positions.append((i, ' ' * indent))

        return return_positions

    def add_autofail_to_file(self, file_path: Path) -> bool:
        """
        Add auto-fail logic to a single detector file.

        Returns True if file was modified, False otherwise.
        """
        with open(file_path, 'r') as f:
            content = f.read()

        # Skip if already has auto-fail logic
        if self.has_autofail_already(content):
            self.skipped_files.append(file_path.name)
            return False

        # Detect variable style
        var_style = self.detect_variable_style(content)

        # Find all return statements that need auto-fail
        return_positions = self.find_return_statements_in_analyze_methods(content, var_style)

        if not return_positions:
            print(f"  ⚠️  {file_path.name}: No return statements found in _analyze methods")
            self.failed_files.append((file_path.name, "No return statements found"))
            return False

        # Add auto-fail logic before each return (process in reverse to maintain line numbers)
        lines = content.split('\n')

        # Process in reverse order to maintain line numbers
        for line_num, indent in reversed(sorted(set(return_positions))):
            # Create the auto-fail block
            autofail_lines = [
                f"{indent}# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0",
                f"{indent}if any(v.get('severity') == 'CRITICAL' for v in {var_style}):",
                f"{indent}    self.score = 0",
                ""  # Empty line
            ]

            # Insert lines in reverse order at the return position
            for autofail_line in reversed(autofail_lines):
                lines.insert(line_num, autofail_line)

        # Write modified content
        modified_content = '\n'.join(lines)

        # Validate Python syntax
        try:
            ast.parse(modified_content)
        except SyntaxError as e:
            print(f"  ❌ {file_path.name}: Syntax error after modification: {e}")
            self.failed_files.append((file_path.name, f"Syntax error: {e}"))
            return False

        # Write the file
        with open(file_path, 'w') as f:
            f.write(modified_content)

        self.modified_files.append((file_path.name, len(set(return_positions))))
        return True

    def run(self) -> dict:
        """Run auto-fail addition on all detectors."""
        print("="*80)
        print("ADDING CRITICAL AUTO-FAIL LOGIC TO ALL DETECTORS")
        print("="*80)
        print()

        # Find all detector files
        detector_files = self.find_detector_files()
        print(f"Found {len(detector_files)} detector files")
        print()

        # Process each file
        for detector_file in detector_files:
            print(f"Processing: {detector_file.name}...", end=" ")

            try:
                if self.add_autofail_to_file(detector_file):
                    count = self.modified_files[-1][1]
                    print(f"✓ Modified ({count} return statements)")
                else:
                    if detector_file.name in [f[0] for f in self.failed_files]:
                        print(f"❌ Failed")
                    else:
                        print(f"⊘ Skipped (already has auto-fail)")
            except Exception as e:
                print(f"❌ Error: {e}")
                self.failed_files.append((detector_file.name, str(e)))

        # Summary
        print()
        print("="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total detectors: {len(detector_files)}")
        print(f"Modified: {len(self.modified_files)}")
        print(f"Skipped (already done): {len(self.skipped_files)}")
        print(f"Failed: {len(self.failed_files)}")
        print()

        if self.modified_files:
            print("✓ MODIFIED FILES:")
            for filename, count in self.modified_files:
                print(f"  - {filename} ({count} methods)")
            print()

        if self.skipped_files:
            print("⊘ SKIPPED FILES (already have auto-fail):")
            for filename in self.skipped_files:
                print(f"  - {filename}")
            print()

        if self.failed_files:
            print("❌ FAILED FILES:")
            for filename, reason in self.failed_files:
                print(f"  - {filename}: {reason}")
            print()

        return {
            'total': len(detector_files),
            'modified': len(self.modified_files),
            'skipped': len(self.skipped_files),
            'failed': len(self.failed_files)
        }


if __name__ == "__main__":
    adder = AutoFailAdder()
    results = adder.run()

    # Exit with error code if any failed
    exit(0 if results['failed'] == 0 else 1)
