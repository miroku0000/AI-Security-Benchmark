#!/usr/bin/env python3
"""
Detector Validation Runner

Runs all detector validation tests and generates comprehensive reports.

Usage:
    python3 scripts/run_detector_validation.py                    # Run all tests
    python3 scripts/run_detector_validation.py --detector sql     # Run specific detector
    python3 scripts/run_detector_validation.py --report-only      # Generate report from previous run
"""

import argparse
import json
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def discover_validation_tests(detector_name=None):
    """
    Discover all detector validation test classes.

    Args:
        detector_name: Optional filter for specific detector

    Returns:
        List of test classes
    """
    test_dir = Path(__file__).parent.parent / 'tests' / 'detector_validation'
    loader = unittest.TestLoader()

    if detector_name:
        # Load specific detector test
        pattern = f'test_*{detector_name}*_validation.py'
    else:
        # Load all validation tests
        pattern = 'test_*_validation.py'

    suite = loader.discover(str(test_dir), pattern=pattern)
    return suite


def run_validation_tests(suite, verbosity=2):
    """
    Run validation test suite.

    Args:
        suite: Test suite to run
        verbosity: Output verbosity level

    Returns:
        TestResult object
    """
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    return result


def generate_summary_report(results_dir='reports/detector_validation'):
    """
    Generate comprehensive summary report from validation results.

    Args:
        results_dir: Directory containing validation result JSON files

    Returns:
        Summary dict
    """
    results_path = Path(results_dir)
    if not results_path.exists():
        print(f"No results directory found at {results_dir}")
        return None

    all_results = []
    for json_file in results_path.glob('*.json'):
        with open(json_file, 'r') as f:
            all_results.append(json.load(f))

    # Aggregate statistics
    total_detectors = len(all_results)
    total_samples = sum(r['total_samples'] for r in all_results)
    total_passed = sum(r['passed'] for r in all_results)
    total_failed = sum(r['failed'] for r in all_results)

    # Find failing detectors
    failing_detectors = [
        {
            'detector': r['detector'],
            'failed_count': r['failed'],
            'total_samples': r['total_samples'],
            'accuracy': (r['passed'] / r['total_samples'] * 100) if r['total_samples'] > 0 else 0
        }
        for r in all_results if r['failed'] > 0
    ]

    # Sort by most failures
    failing_detectors.sort(key=lambda x: x['failed_count'], reverse=True)

    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_detectors_tested': total_detectors,
        'total_samples': total_samples,
        'total_passed': total_passed,
        'total_failed': total_failed,
        'overall_accuracy': (total_passed / total_samples * 100) if total_samples > 0 else 0,
        'failing_detectors': failing_detectors,
        'all_results': all_results
    }

    return summary


def print_summary_report(summary):
    """Print formatted summary report to console."""
    print("\n" + "=" * 80)
    print("DETECTOR VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Timestamp: {summary['timestamp']}")
    print(f"Detectors Tested: {summary['total_detectors_tested']}")
    print(f"Total Samples: {summary['total_samples']}")
    print(f"Passed: {summary['total_passed']}")
    print(f"Failed: {summary['total_failed']}")
    print(f"Overall Accuracy: {summary['overall_accuracy']:.1f}%")
    print()

    if summary['failing_detectors']:
        print("=" * 80)
        print("FAILING DETECTORS (REQUIRES IMMEDIATE FIX)")
        print("=" * 80)
        for detector in summary['failing_detectors']:
            print(f"\n❌ {detector['detector']}")
            print(f"   Accuracy: {detector['accuracy']:.1f}% ({detector['failed_count']}/{detector['total_samples']} failures)")
            print(f"   Impact: This detector is producing false results in benchmark")
    else:
        print("✅ All detectors passing validation tests!")

    print("\n" + "=" * 80)


def save_summary_report(summary, output_path='reports/detector_validation_summary.json'):
    """Save summary report to JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\n📄 Full report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Run detector validation tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 scripts/run_detector_validation.py                    # Run all tests
  python3 scripts/run_detector_validation.py --detector sql     # Test SQLInjectionDetector only
  python3 scripts/run_detector_validation.py --report-only      # Generate report without running tests
  python3 scripts/run_detector_validation.py --verbose          # Increase output detail
        '''
    )
    parser.add_argument(
        '--detector',
        type=str,
        help='Run validation for specific detector (e.g., "sql", "xxe", "xss")'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Generate report from existing results without running tests'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Increase output verbosity'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='reports/detector_validation_summary.json',
        help='Path to save summary report'
    )

    args = parser.parse_args()

    if not args.report_only:
        print("=" * 80)
        print("RUNNING DETECTOR VALIDATION TESTS")
        print("=" * 80)
        if args.detector:
            print(f"Detector filter: {args.detector}")
        print()

        # Discover and run tests
        suite = discover_validation_tests(args.detector)
        verbosity = 2 if args.verbose else 1
        result = run_validation_tests(suite, verbosity)

        # Print immediate results
        print("\n" + "=" * 80)
        if result.wasSuccessful():
            print("✅ ALL DETECTOR VALIDATION TESTS PASSED")
            print("=" * 80)
            print("All detectors are correctly identifying vulnerabilities.")
            print("Benchmark results can be trusted for validated detectors.")
        else:
            print("❌ DETECTOR VALIDATION TESTS FAILED")
            print("=" * 80)
            print(f"Failures: {len(result.failures)}")
            print(f"Errors: {len(result.errors)}")
            print()
            print("CRITICAL: Detectors have accuracy issues that MUST be fixed.")
            print("Benchmark results are INVALID until detectors are corrected.")

    # Generate summary report
    print("\n" + "=" * 80)
    print("GENERATING SUMMARY REPORT")
    print("=" * 80)

    summary = generate_summary_report()
    if summary:
        print_summary_report(summary)
        save_summary_report(summary, args.output)

        # Exit with error code if any detectors failing
        if summary['failing_detectors']:
            sys.exit(1)
    else:
        print("No validation results found. Run tests first.")
        if args.report_only:
            sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
