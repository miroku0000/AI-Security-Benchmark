#!/usr/bin/env python3
"""
Example: How to test your SAST scanner against the AI Security Benchmark

This script demonstrates how to run your SAST tool against our vulnerable files
and compare the results to our ground truth.
"""

import json
import subprocess
import os
from pathlib import Path

def run_semgrep_example():
    """Example: Running Semgrep against SQL injection files."""

    # Step 1: Run Semgrep against SQL injection files
    print("Step 1: Running Semgrep against SQL injection vulnerable files...")

    sql_injection_dir = "testsast/knownbad/sql_injection"
    if not os.path.exists(sql_injection_dir):
        print(f"Directory {sql_injection_dir} not found. Run generate_sast_testsuite.py first.")
        return

    # Run Semgrep with SQL injection rules
    cmd = [
        "semgrep",
        "--config=p/sql-injection",
        "--json",
        "--output=semgrep_sql_results.json",
        sql_injection_dir
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✓ Semgrep scan completed")
    except subprocess.CalledProcessError as e:
        print(f"Semgrep failed: {e}")
        print("Make sure Semgrep is installed: pip install semgrep")
        return
    except FileNotFoundError:
        print("Semgrep not found. Install with: pip install semgrep")
        return

    # Step 2: Compare results
    print("\nStep 2: Comparing Semgrep results to benchmark...")

    cmd = [
        "python3", "sast_comparison.py",
        "--benchmark", "testsast/reports.json",
        "--sast-results", "semgrep_sql_results.json",
        "--format", "semgrep",
        "--category", "sql_injection",
        "--output", "semgrep_comparison_report.txt"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)

    if result.returncode == 0:
        print("✓ Comparison completed! Check semgrep_comparison_report.txt")
    else:
        print(f"Comparison failed: {result.stderr}")

def run_custom_scanner_example():
    """Example: Testing a custom scanner that outputs simple JSON."""

    # Create mock SAST results for demonstration
    mock_results = [
        {
            "file": "testsast/knownbad/sql_injection/python/gpt-4_sql_001_score00.py",
            "line": 15,
            "rule": "SQL_INJECTION",
            "severity": "HIGH",
            "message": "Potential SQL injection vulnerability"
        },
        {
            "file": "testsast/knownbad/xss/javascript/claude-sonnet-4-5_xss_002_score01.js",
            "line": 8,
            "rule": "XSS",
            "severity": "MEDIUM",
            "message": "Potential XSS vulnerability"
        }
    ]

    # Save mock results
    with open('mock_scanner_results.json', 'w') as f:
        json.dump(mock_results, f, indent=2)

    print("Created mock scanner results...")

    # Compare against benchmark
    cmd = [
        "python3", "sast_comparison.py",
        "--benchmark", "testsast/reports.json",
        "--sast-results", "mock_scanner_results.json",
        "--format", "custom",
        "--file-field", "file",
        "--line-field", "line",
        "--type-field", "rule",
        "--severity-field", "severity",
        "--desc-field", "message"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)

    # Cleanup
    os.remove('mock_scanner_results.json')

def show_available_categories():
    """Show what vulnerability categories are available for testing."""

    if not os.path.exists("testsast/knownbad"):
        print("testsast/knownbad directory not found. Run generate_sast_testsuite.py first.")
        return

    categories = [d for d in os.listdir("testsast/knownbad") if os.path.isdir(f"testsast/knownbad/{d}")]

    print("Available vulnerability categories for testing:")
    print("=" * 50)

    for category in sorted(categories):
        category_path = f"testsast/knownbad/{category}"

        # Count files in category
        file_count = 0
        for root, dirs, files in os.walk(category_path):
            file_count += len([f for f in files if not f.startswith('.')])

        print(f"{category:<30} ({file_count} files)")

def main():
    print("AI Security Benchmark - SAST Testing Examples")
    print("=" * 50)

    print("\n1. Available vulnerability categories:")
    show_available_categories()

    print("\n2. Example Semgrep test (requires Semgrep installation):")
    print("   python3 example_sast_test.py semgrep")

    print("\n3. Example custom scanner test:")
    print("   python3 example_sast_test.py custom")

    print("\n4. Manual testing:")
    print("   # Run your SAST tool against testsast/knownbad/<category>/")
    print("   # Then compare: python3 sast_comparison.py --benchmark testsast/reports.json --sast-results your_results.json --format <format>")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "semgrep":
            run_semgrep_example()
        elif sys.argv[1] == "custom":
            run_custom_scanner_example()
        else:
            print(f"Unknown command: {sys.argv[1]}")
    else:
        main()