#!/usr/bin/env python3
"""
Test runner for all SAST UI tests
Runs both the main workflow test and edge case tests
"""

import unittest
import sys
from pathlib import Path

def run_all_tests():
    """Run all UI tests and return success status"""
    print("🧪 Running SAST UI Automated Tests")
    print("=" * 50)

    # Discover and run all tests
    loader = unittest.TestLoader()
    suite = loader.discover('.', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 50)

    if result.wasSuccessful():
        print("✅ All tests passed!")
        print(f"📊 Ran {result.testsRun} tests with 0 failures and 0 errors")
        return True
    else:
        print("❌ Some tests failed!")
        print(f"📊 Ran {result.testsRun} tests with {len(result.failures)} failures and {len(result.errors)} errors")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)