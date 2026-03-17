#!/usr/bin/env python3
"""
Quick test of SAST analysis on a few files to validate the approach
"""

import sys
sys.path.insert(0, '.')

from analyze_sast_accuracy import (
    load_ground_truth, load_sast_findings, analyze_file
)

# Test on chatgpt-4o-latest with just 2 files
model_name = 'chatgpt-4o-latest'
test_files = ['sql_001.py', 'cmd_001.py']  # One SQL injection, one command injection

print("="*80)
print("SAST Accuracy Test - Limited Run")
print("="*80)

# Load data
print("\n1. Loading ground truth...")
ground_truth = load_ground_truth(model_name)
if not ground_truth:
    sys.exit(1)
print(f"   ✓ Loaded {len(ground_truth)} ground truth files")

print("\n2. Loading SAST findings...")
sast_findings = load_sast_findings(model_name)
if not sast_findings:
    sys.exit(1)
print(f"   ✓ Loaded SAST findings for {len(sast_findings)} files")

# Analyze test files
print(f"\n3. Analyzing {len(test_files)} test files...")
for filename in test_files:
    if filename not in ground_truth:
        print(f"   ✗ {filename} not in ground truth")
        continue

    if filename not in sast_findings:
        print(f"   ✗ {filename} has no SAST findings")
        continue

    result = analyze_file(
        filename,
        ground_truth[filename],
        sast_findings[filename],
        model_name
    )

print("\n" + "="*80)
print("Test complete!")
