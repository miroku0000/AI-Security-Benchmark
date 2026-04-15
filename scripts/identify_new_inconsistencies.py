#!/usr/bin/env python3
"""
Identify the 8 tests that moved from "always secure" to "inconsistent"
between Iteration 8 and Iteration 9.

This script compares the cross-model validation results to understand
why the fixes made the problem worse.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def load_comparison(file_path: str) -> dict:
    """Load cross-model comparison JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def get_test_status(comparison: dict) -> dict:
    """
    Extract test status from comparison results.
    Returns dict: {test_id: 'always_secure' | 'always_vulnerable' | 'inconsistent'}
    """
    status = {}

    for test_id in comparison.get('always_secure', []):
        status[test_id] = 'always_secure'

    for test_id in comparison.get('always_vulnerable', []):
        status[test_id] = 'always_vulnerable'

    for item in comparison.get('inconsistent_verdicts', []):
        test_id = item.get('test_id')
        if test_id:
            status[test_id] = 'inconsistent'

    return status


def find_status_changes(before: dict, after: dict) -> dict:
    """
    Find tests that changed status between iterations.

    Returns dict with categories:
    - secure_to_inconsistent: Tests that were always secure, now inconsistent
    - inconsistent_to_secure: Tests that were inconsistent, now always secure
    - etc.
    """
    changes = defaultdict(list)

    all_tests = set(before.keys()) | set(after.keys())

    for test_id in sorted(all_tests):
        before_status = before.get(test_id, 'unknown')
        after_status = after.get(test_id, 'unknown')

        if before_status != after_status:
            change_key = f"{before_status}_to_{after_status}"
            changes[change_key].append(test_id)

    return dict(changes)


def main():
    # Load Iteration 8 results (original detectors)
    iter8_file = Path("reports/iteration8_cross_model_comparison.json")

    if not iter8_file.exists():
        print(f"ERROR: {iter8_file} not found")
        print("Run cross-model validation on Iteration 8 results first")
        return 1

    print("Loading Iteration 8 results (BEFORE fixes)...")
    iter8_data = load_comparison(str(iter8_file))
    iter8_status = get_test_status(iter8_data)

    # Create Iteration 9 results by re-running cross_model_validation.py
    # For now, use the output we just generated
    print("\nNote: Iteration 9 results should be in iteration8_cross_model_comparison.json")
    print("(it was overwritten by the latest run)")
    print("\nTo properly compare, we need to:")
    print("1. Rename current iteration8_cross_model_comparison.json to iteration9_...")
    print("2. Re-run cross-model validation on ORIGINAL (pre-fix) detector results")
    print("\nFor now, showing methodology...")

    # Methodology example
    print("\n" + "="*80)
    print("METHODOLOGY")
    print("="*80)
    print("""
To identify the 8 new inconsistencies:

1. BASELINE (Iteration 8 - Original Detectors):
   Load: reports/iteration8_cross_model_comparison.json (from original run)
   Extract: List of 'always_secure' tests (263 tests)

2. AFTER FIXES (Iteration 9 - Fixed Detectors):
   Load: reports/iteration9_cross_model_comparison.json (from re-validation)
   Extract: List of 'always_secure' tests (255 tests)

3. FIND MISSING TESTS:
   Compare lists to find 8 tests present in Iteration 8 but missing from Iteration 9

4. VERIFY THEY MOVED TO 'INCONSISTENT':
   Check these 8 tests appear in Iteration 9's 'inconsistent_verdicts' list

5. ANALYZE CHARACTERISTICS:
   - Which categories are they from?
   - Which detector do they use?
   - Did they trigger syntax validation?
   - Did they have comments filtered?

6. MANUAL REVIEW:
   For each of the 8 tests, examine:
   - Implementation across all 6 models
   - Why they were consistent before (all SECURE)
   - Why they're inconsistent now (mixed verdicts)
   - Which specific fix caused the change
""")

    print("\n" + "="*80)
    print("EXAMPLE ANALYSIS TEMPLATE")
    print("="*80)
    print("""
Test: example_test_001
Category: broken_access_control
Detector: AccessControlDetector

Iteration 8 Status: ALWAYS SECURE (6/6 models)
- claude-opus-4-6:     SECURE (2/2)
- claude-sonnet-4-5:   SECURE (2/2)
- cursor:              SECURE (2/2)
- deepseek-coder:      SECURE (2/2)
- gpt-4o:              SECURE (2/2)
- gpt-5.4:             SECURE (2/2)

Iteration 9 Status: INCONSISTENT (4 SECURE / 2 VULNERABLE)
- claude-opus-4-6:     SECURE (2/2)
- claude-sonnet-4-5:   VULNERABLE (1/2)  ← CHANGED
- cursor:              SECURE (2/2)
- deepseek-coder:      SECURE (2/2)
- gpt-4o:              SECURE (2/2)
- gpt-5.4:             VULNERABLE (0/2)  ← CHANGED

Analysis:
- Two models changed from SECURE to VULNERABLE
- Likely triggered by syntax validation fix (universal_fallback detector)
- OR comment filtering removed comments that detector relied on
- Need to inspect implementations to determine root cause

Root Cause: [TBD after manual inspection]

Recommendation: [Revert fix | Keep fix | Refine detector logic]
""")

    print("\n" + "="*80)
    print("ACTION ITEMS")
    print("="*80)
    print("""
To complete this analysis:

1. Save current iteration8_cross_model_comparison.json as iteration9_...
2. Re-run cross-model validation on ORIGINAL detector results
3. Run this script with both files available
4. Script will automatically identify the 8 tests
5. Manual review each test following template above
6. Document findings in iteration9_8_new_inconsistencies.md
""")

    print("\n" + "="*80)
    print("STATISTICS FROM ITERATION 8 (BEFORE)")
    print("="*80)
    print(f"Total tests: {iter8_data.get('total_tests', 0)}")
    print(f"Always secure: {len(iter8_data.get('always_secure', []))}")
    print(f"Always vulnerable: {len(iter8_data.get('always_vulnerable', []))}")
    print(f"Inconsistent: {len(iter8_data.get('inconsistent_verdicts', []))}")

    print("\nTo run full analysis once files are available:")
    print("  python3 scripts/identify_new_inconsistencies.py --before iter8.json --after iter9.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
