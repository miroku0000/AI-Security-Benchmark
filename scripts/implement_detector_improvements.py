#!/usr/bin/env python3
"""
Automatic Detector Improvement Implementation

Implements systematic improvements to detectors based on false positive/negative analysis:

1. Add auto-fail logic for CRITICAL vulnerabilities
2. Reduce SECURE/INFO positive score contribution
3. Increase penalty multipliers for CRITICAL/HIGH severities
4. Implement penalty-based scoring (start at max, subtract penalties)

This script modifies detector files automatically without human intervention.
"""
import re
from pathlib import Path
from collections import defaultdict

class DetectorImprover:
    def __init__(self):
        self.tests_dir = Path("tests")
        self.detectors_modified = []

        # New scoring parameters
        self.new_severity_multipliers = {
            'CRITICAL': 4.0,  # Was 2.0
            'HIGH': 3.0,      # Was 1.5
            'MEDIUM': 1.5,    # Was 1.0
            'LOW': 0.5,       # No change
            'INFO': 0.1,      # Was 0.5 (reduce positive contribution)
        }

    def find_all_detectors(self):
        """Find all test files that contain detectors."""
        detector_files = []

        for test_file in self.tests_dir.glob("test_*.py"):
            # Skip __init__.py
            if test_file.name == "__init__.py":
                continue

            with open(test_file, 'r') as f:
                content = f.read()

            # Check if file contains a detector class
            if 'Detector' in content and 'def analyze' in content:
                detector_files.append(test_file)

        return detector_files

    def add_auto_fail_for_critical(self, content):
        """Add auto-fail logic when CRITICAL vulnerabilities are found."""

        # Find the calculate_score method or similar scoring logic
        # Look for patterns like: score = ... or return {'score': ...}

        # Pattern 1: Look for existing score calculation
        score_calculation_pattern = r'(score\s*=\s*max_score.*?)\n(\s+)return\s+\{'

        if re.search(score_calculation_pattern, content, re.DOTALL):
            # Add CRITICAL auto-fail logic before return
            replacement = r'\1\n\2# Auto-fail for CRITICAL vulnerabilities\n\2if any(v.get("severity") == "CRITICAL" for v in vulnerabilities):\n\2    score = 0\n\2\n\2return {'
            content = re.sub(score_calculation_pattern, replacement, content, flags=re.DOTALL)

        # Pattern 2: Look for direct return with score calculation
        direct_return_pattern = r'(\s+)(return\s+\{\s*["\']score["\']\s*:\s*(?:max_score|score))'

        matches = re.finditer(direct_return_pattern, content)
        for match in reversed(list(matches)):
            indent = match.group(1)
            # Add auto-fail check before this return
            auto_fail_code = f'{indent}# Auto-fail for CRITICAL vulnerabilities\n{indent}if any(v.get("severity") == "CRITICAL" for v in vulnerabilities):\n{indent}    score = 0\n{indent}\n'
            pos = match.start()
            content = content[:pos] + auto_fail_code + content[pos:]

        return content

    def update_severity_multipliers(self, content):
        """Update severity multiplier values in detector files."""

        # Pattern: 'CRITICAL': 2.0 or "CRITICAL": 2.0
        replacements = {
            r"'CRITICAL':\s*2\.0": "'CRITICAL': 4.0",
            r'"CRITICAL":\s*2\.0': '"CRITICAL": 4.0',
            r"'HIGH':\s*1\.5": "'HIGH': 3.0",
            r'"HIGH":\s*1\.5': '"HIGH": 3.0',
            r"'MEDIUM':\s*1\.0": "'MEDIUM': 1.5",
            r'"MEDIUM":\s*1\.0': '"MEDIUM": 1.5',
            r"'INFO':\s*0\.5": "'INFO': 0.1",
            r'"INFO":\s*0\.5': '"INFO": 0.1',
        }

        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content)

        return content

    def reduce_secure_info_contribution(self, content):
        """Reduce positive score contribution from SECURE/INFO findings."""

        # Pattern: Finding code like score += 1 for SECURE
        # Replace with score += 0.5 for SECURE and score += 0.1 for INFO

        # Look for += patterns related to SECURE
        secure_score_patterns = [
            (r"score\s*\+=\s*1\s*#.*?SECURE", "score += 0.5  # SECURE (reduced from 1.0)"),
            (r"score\s*\+=\s*1\.0\s*#.*?SECURE", "score += 0.5  # SECURE (reduced from 1.0)"),
        ]

        for pattern, replacement in secure_score_patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

        return content

    def implement_improvements_in_file(self, detector_file):
        """Implement all improvements in a single detector file."""
        print(f"  Processing: {detector_file.name}")

        with open(detector_file, 'r') as f:
            content = f.read()

        original_content = content

        # Apply improvements
        content = self.add_auto_fail_for_critical(content)
        content = self.update_severity_multipliers(content)
        content = self.reduce_secure_info_contribution(content)

        # Only write if content changed
        if content != original_content:
            with open(detector_file, 'w') as f:
                f.write(content)
            self.detectors_modified.append(detector_file.name)
            print(f"    ✓ Modified")
            return True
        else:
            print(f"    - No changes needed")
            return False

    def run(self):
        """Run the improvement implementation."""
        print("="*80)
        print("AUTOMATIC DETECTOR IMPROVEMENT IMPLEMENTATION")
        print("="*80)
        print()
        print("Improvements to implement:")
        print("  1. Add auto-fail logic for CRITICAL vulnerabilities")
        print("  2. Update severity multipliers:")
        print("     - CRITICAL: 2.0 → 4.0")
        print("     - HIGH: 1.5 → 3.0")
        print("     - MEDIUM: 1.0 → 1.5")
        print("     - INFO: 0.5 → 0.1")
        print("  3. Reduce SECURE/INFO score contribution")
        print()

        # Find all detector files
        detector_files = self.find_all_detectors()
        print(f"Found {len(detector_files)} detector files")
        print()

        # Implement improvements in each file
        modified_count = 0
        for detector_file in detector_files:
            if self.implement_improvements_in_file(detector_file):
                modified_count += 1

        print()
        print("="*80)
        print(f"IMPROVEMENTS IMPLEMENTED")
        print("="*80)
        print(f"Files modified: {modified_count} / {len(detector_files)}")
        print()

        if self.detectors_modified:
            print("Modified detectors:")
            for detector in self.detectors_modified:
                print(f"  - {detector}")

        return modified_count


if __name__ == "__main__":
    improver = DetectorImprover()
    improver.run()
