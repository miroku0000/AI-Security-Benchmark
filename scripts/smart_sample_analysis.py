#!/usr/bin/env python3
"""
Smart Sampling Strategy for Cost-Effective LLM Analysis

This script implements intelligent sampling to reduce costs while maximizing
detection of false positives and false negatives.
"""

import json
import random
import argparse
from pathlib import Path
from typing import Dict, List

def smart_sample(data: List[Dict], sample_size: int = 100) -> List[Dict]:
    """
    Intelligently sample tests to maximize FP/FN detection while minimizing cost.

    Priority order:
    1. FAILURES (most likely to be false positives)
    2. EDGE CASES (near pass/fail threshold)
    3. PASSES (lower priority, but need some coverage)
    """

    # Separate by primary detector result
    failures = []
    passes = []
    edge_cases = []

    for test in data:
        primary_result = test.get('primary_detector_result')
        primary_score = test.get('primary_detector_score', test.get('score', 0))
        primary_max = test.get('primary_detector_max_score', test.get('max_score', 2))

        # Edge case: score is exactly at threshold
        if primary_score == primary_max / 2:
            edge_cases.append(test)
        elif primary_result == 'FAIL' or (primary_result is None and primary_score < primary_max / 2):
            failures.append(test)
        elif primary_result == 'PASS' or (primary_result is None and primary_score >= primary_max / 2):
            passes.append(test)

    print(f"Total tests: {len(data)}")
    print(f"  Failures: {len(failures)}")
    print(f"  Passes: {len(passes)}")
    print(f"  Edge cases: {len(edge_cases)}")
    print()

    # Allocate sample budget
    # 50% failures, 20% edge cases, 30% passes
    failure_budget = int(sample_size * 0.5)
    edge_budget = int(sample_size * 0.2)
    pass_budget = sample_size - failure_budget - edge_budget

    # Sample with priority
    sampled_failures = failures[:failure_budget]
    sampled_edge = edge_cases[:edge_budget]

    # Random sample of passes for coverage
    sampled_passes = random.sample(passes, min(pass_budget, len(passes)))

    # Combine
    sample = sampled_failures + sampled_edge + sampled_passes

    print(f"Sample composition ({len(sample)} total):")
    print(f"  Failures: {len(sampled_failures)} ({len(sampled_failures)/len(sample)*100:.1f}%)")
    print(f"  Edge cases: {len(sampled_edge)} ({len(sampled_edge)/len(sample)*100:.1f}%)")
    print(f"  Passes: {len(sampled_passes)} ({len(sampled_passes)/len(sample)*100:.1f}%)")

    return sample

def category_stratified_sample(data: List[Dict], sample_size: int = 100) -> List[Dict]:
    """
    Sample evenly across categories to ensure all vulnerability types are tested.
    """

    # Group by category
    by_category = {}
    for test in data:
        cat = test.get('category', 'unknown')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(test)

    # Calculate per-category sample size
    num_categories = len(by_category)
    per_category = sample_size // num_categories

    print(f"Category-stratified sampling:")
    print(f"  {num_categories} categories")
    print(f"  ~{per_category} samples per category")
    print()

    sample = []
    for cat, tests in by_category.items():
        # Within each category, prioritize failures
        cat_failures = [t for t in tests if t.get('primary_detector_result') == 'FAIL']
        cat_passes = [t for t in tests if t.get('primary_detector_result') == 'PASS']

        # 70% failures, 30% passes within each category
        fail_budget = int(per_category * 0.7)
        pass_budget = per_category - fail_budget

        cat_sample = cat_failures[:fail_budget] + cat_passes[:pass_budget]
        sample.extend(cat_sample)

    print(f"Total sampled: {len(sample)}")
    return sample

def main():
    parser = argparse.ArgumentParser(description="Smart sampling for LLM analysis")
    parser.add_argument("analysis_file", help="Path to analysis JSON file")
    parser.add_argument("--sample-size", "-s", type=int, default=100,
                       help="Number of tests to sample (default: 100)")
    parser.add_argument("--strategy", choices=['priority', 'stratified'], default='priority',
                       help="Sampling strategy: priority (focus on failures) or stratified (even across categories)")
    parser.add_argument("--output", "-o", help="Output file for sampled data", required=True)
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)

    # Load analysis data
    with open(args.analysis_file, 'r') as f:
        raw_data = json.load(f)

    # Extract detailed results
    if isinstance(raw_data, dict) and 'detailed_results' in raw_data:
        data = raw_data['detailed_results']
    elif isinstance(raw_data, list):
        data = raw_data
    else:
        print("ERROR: Unexpected data format")
        return

    print(f"Loaded {len(data)} tests from {args.analysis_file}")
    print()

    # Apply sampling strategy
    if args.strategy == 'priority':
        sample = smart_sample(data, args.sample_size)
    else:
        sample = category_stratified_sample(data, args.sample_size)

    # Save sampled data in same format as original
    output_data = raw_data.copy() if isinstance(raw_data, dict) else {}
    output_data['detailed_results'] = sample

    # Update summary if present
    if isinstance(raw_data, dict) and 'summary' in raw_data:
        output_data['summary'] = {
            **raw_data['summary'],
            'sampled': True,
            'sample_size': len(sample),
            'sample_strategy': args.strategy,
            'original_size': len(data)
        }

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nSampled data saved to: {output_path}")
    print(f"\nNext step:")
    print(f"  python3 scripts/llm_analyze_false_results.py \\")
    print(f"    <model_name> {output_path} \\")
    print(f"    --output reports/refinement/iteration1.json")

if __name__ == "__main__":
    main()
