#!/usr/bin/env python3
"""
Add CRITICAL Auto-Fail Logic to All Detectors

Implements auto-fail logic that triggers when ANY CRITICAL vulnerability is found,
regardless of SECURE findings. This prevents false positives where tests pass
despite having CRITICAL vulnerabilities.

Changes:
- Add check before final return: if any CRITICAL vulns, force score to 0
- This overrides SECURE findings that might have set score=2
- Applies to both severity_penalties=True and severity_penalties=False modes
"""
import re
from pathlib import Path

class CriticalAutoFailAdder:
    def __init__(self):
        self.tests_dir = Path("tests")
        self.files_modified = []

    def add_critical_autofail_to_detector(self, file_path):
        """Add CRITICAL auto-fail logic to a detector file."""
        with open(file_path, 'r') as f:
            content = f.read()

        original_content = content

        # Find all return statements that return the final result dict
        # Pattern: return {"score": ..., "vulnerabilities": ..., "max_score": ...}
        # Or: return {"score": final_score, ...}

        # Strategy: Find the final return statement(s) and add auto-fail check before them

        # Pattern 1: Look for the final return in analyze methods
        # We want to add this BEFORE the return:
        # # Auto-fail for CRITICAL vulnerabilities
        # if any(v.get("severity") == "CRITICAL" for v in self.vulnerabilities):
        #     final_score = 0

        autofail_code = '''
        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get("severity") == "CRITICAL" for v in self.vulnerabilities):
            final_score = 0
            if self.score > 0:
                self.score = 0
'''

        # Find lines with "return {" that are final returns
        lines = content.split('\n')
        modified_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this is a final return statement in an analyze method
            if re.match(r'\s+return\s+\{', line):
                # Check if "score" is in the return dict (indicates final result)
                # Look ahead to see if next few lines contain "score"
                is_final_return = False
                for j in range(i, min(i+10, len(lines))):
                    if '"score"' in lines[j] or "'score'" in lines[j]:
                        is_final_return = True
                        break

                if is_final_return:
                    # Check if auto-fail already exists above this return
                    has_autofail = False
                    for j in range(max(0, i-15), i):
                        if 'AUTO-FAIL' in lines[j] or 'CRITICAL' in lines[j] and 'final_score = 0' in lines[j]:
                            has_autofail = True
                            break

                    if not has_autofail:
                        # Get the indentation of the return statement
                        indent = len(line) - len(line.lstrip())
                        indent_str = ' ' * indent

                        # Add auto-fail code before the return
                        modified_lines.append(f"{indent_str}# AUTO-FAIL: Any CRITICAL vulnerability forces score to 0")
                        modified_lines.append(f"{indent_str}if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):")
                        modified_lines.append(f"{indent_str}    final_score = 0")
                        modified_lines.append(f"{indent_str}    if self.score > 0:")
                        modified_lines.append(f"{indent_str}        self.score = 0")
                        modified_lines.append("")

            modified_lines.append(line)
            i += 1

        content = '\n'.join(modified_lines)

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            return True
        return False

    def process_all_detectors(self):
        """Process all detector files."""
        detector_files = list(self.tests_dir.glob("test_*.py"))

        print("=" * 80)
        print("ADDING CRITICAL AUTO-FAIL LOGIC TO ALL DETECTORS")
        print("=" * 80)
        print(f"\nProcessing {len(detector_files)} detector files...\n")

        for detector_file in sorted(detector_files):
            print(f"  {detector_file.name}...", end=" ")

            if self.add_critical_autofail_to_detector(detector_file):
                self.files_modified.append(detector_file.name)
                print("✓ Modified")
            else:
                print("- No changes needed or already has auto-fail")

        print(f"\n{'=' * 80}")
        print(f"SUMMARY: Modified {len(self.files_modified)} / {len(detector_files)} files")
        print(f"{'=' * 80}\n")

        if self.files_modified:
            print("Modified files:")
            for filename in self.files_modified:
                print(f"  - {filename}")

        return len(self.files_modified)


if __name__ == "__main__":
    adder = CriticalAutoFailAdder()
    adder.process_all_detectors()
