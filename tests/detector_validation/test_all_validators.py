#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

validator_dir = Path("tests/detector_validation")
test_files = sorted(validator_dir.glob("test_*_detector_validation.py"))
print(f"Found {len(test_files)} validator tests\n")
passed, failed = [], []

for test_file in test_files:
    test_name = test_file.stem.replace("test_", "").replace("_detector_validation", "")
    try:
        result = subprocess.run(["python3", str(test_file)], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            passed.append(test_name)
            print(f"✅ {test_name:50} PASSED")
        else:
            failed.append(test_name)
            print(f"❌ {test_name:50} FAILED")
    except:
        failed.append(test_name)
        print(f"⏱️  {test_name:50} TIMEOUT/ERROR")

print(f"\nResults: {len(passed)} PASSED, {len(failed)} FAILED out of {len(test_files)} total")
if failed:
    print(f"\nFailed tests: {', '.join(failed)}")
    sys.exit(1)
else:
    print("\n🎉 All validator tests PASSED!")
    sys.exit(0)
