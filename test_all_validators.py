#!/usr/bin/env python3
"""
Run all detector validation tests and report results.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_validator_tests():
    """Run all validator tests and collect results."""
    validator_dir = Path("tests/detector_validation")

    # Find all test files
    test_files = sorted(validator_dir.glob("test_*_detector_validation.py"))

    print(f"Found {len(test_files)} validator tests\n")
    print("=" * 80)

    passed = []
    failed = []

    for test_file in test_files:
        test_name = test_file.stem.replace("test_", "").replace("_detector_validation", "")

        try:
            # Run the test
            result = subprocess.run(
                ["python3", str(test_file)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                passed.append(test_name)
                print(f"✅ {test_name:50} PASSED")
            else:
                failed.append(test_name)
                print(f"❌ {test_name:50} FAILED")
                # Print error details
                if "FAILED" in result.stdout:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if "AssertionError" in line or "expected" in line.lower():
                            print(f"   {line.strip()}")

        except subprocess.TimeoutExpired:
            failed.append(test_name)
            print(f"⏱️  {test_name:50} TIMEOUT")
        except Exception as e:
            failed.append(test_name)
            print(f"💥 {test_name:50} ERROR: {e}")

    print("=" * 80)
    print(f"\nResults: {len(passed)} PASSED, {len(failed)} FAILED out of {len(test_files)} total")

    if failed:
        print(f"\nFailed tests:")
        for name in failed:
            print(f"  - {name}")
        return 1
    else:
        print("\n🎉 All validator tests PASSED!")
        return 0

if __name__ == "__main__":
    sys.exit(run_validator_tests())
