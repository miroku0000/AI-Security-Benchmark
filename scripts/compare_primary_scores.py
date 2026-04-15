#!/usr/bin/env python3
"""
Compare PRIMARY detector scores across models to identify inconsistencies.
This script filters for tests where max_score=2 (primary detector only).
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def load_primary_results(file_path: str) -> dict:
    """Load validation results and extract PRIMARY detector scores only."""
    with open(file_path, 'r') as f:
        data = json.load(f)

    results = {}
    if 'detailed_results' in data:
        for item in data['detailed_results']:
            test_id = item.get('prompt_id')
            max_score = item.get('max_score', 0)

            # ONLY include PRIMARY detector scores (max_score=2)
            if test_id and max_score == 2:
                results[test_id] = {
                    'score': item.get('score', 0),
                    'max_score': max_score,
                    'category': item.get('category', 'unknown'),
                    'verdict': 'PASS' if item.get('score', 0) >= max_score else 'FAIL'
                }

    return results


def compare_models(model_results: dict) -> dict:
    """Compare PRIMARY detector results across models."""

    # Get all test IDs that have PRIMARY scores
    all_test_ids = set()
    for results in model_results.values():
        all_test_ids.update(results.keys())

    comparison = {
        'total_tests': len(all_test_ids),
        'always_pass': [],
        'always_fail': [],
        'inconsistent': []
    }

    for test_id in sorted(all_test_ids):
        verdicts = []
        model_data = {}

        for model_name, results in model_results.items():
            if test_id in results:
                verdict = results[test_id]['verdict']
                verdicts.append(verdict)
                model_data[model_name] = {
                    'verdict': verdict,
                    'score': f"{results[test_id]['score']}/{results[test_id]['max_score']}",
                    'category': results[test_id]['category']
                }

        if len(verdicts) < 2:
            continue

        unique_verdicts = set(verdicts)

        if len(unique_verdicts) == 1:
            # All models agree
            if 'PASS' in unique_verdicts:
                comparison['always_pass'].append(test_id)
            else:
                comparison['always_fail'].append(test_id)
        else:
            # Inconsistent verdicts
            pass_count = verdicts.count('PASS')
            fail_count = verdicts.count('FAIL')
            category = list(model_data.values())[0]['category']

            comparison['inconsistent'].append({
                'test_id': test_id,
                'category': category,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'models': model_data
            })

    return comparison


def print_report(comparison: dict, models: list):
    """Print formatted report."""

    print("=" * 100)
    print("ITERATION 10: PRIMARY DETECTOR CROSS-MODEL VALIDATION")
    print("=" * 100)
    print(f"\nModels Compared: {', '.join(models)}")
    print(f"Total Tests Analyzed (PRIMARY detector only, max_score=2): {comparison['total_tests']}")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("-" * 100)

    num_inconsistent = len(comparison['inconsistent'])
    num_always_pass = len(comparison['always_pass'])
    num_always_fail = len(comparison['always_fail'])
    total_consistent = num_always_pass + num_always_fail

    print(f"✅ Always PASS (Consistent):  {num_always_pass:4d} ({num_always_pass*100//comparison['total_tests']:2d}%)")
    print(f"❌ Always FAIL (Consistent):  {num_always_fail:4d} ({num_always_fail*100//comparison['total_tests']:2d}%)")
    print(f"⚠️  Inconsistent (PASS/FAIL): {num_inconsistent:4d} ({num_inconsistent*100//comparison['total_tests']:2d}%)")
    print(f"\n📊 Total Consistent: {total_consistent}/{comparison['total_tests']} ({total_consistent*100//comparison['total_tests']:.1f}%)")

    # Split pattern analysis
    if comparison['inconsistent']:
        print("\n" + "=" * 100)
        print("SPLIT PATTERN ANALYSIS")
        print("-" * 100)

        split_counts = defaultdict(int)
        for item in comparison['inconsistent']:
            split = f"{item['pass_count']}-{item['fail_count']}"
            split_counts[split] += 1

        print(f"{'Split Pattern':<15s} {'Count':>6s} {'Interpretation'}")
        print("-" * 100)
        for split in sorted(split_counts.keys(), key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1]))):
            count = split_counts[split]

            parts = split.split('-')
            p, f = int(parts[0]), int(parts[1])

            if p == f:
                interp = f"50/50 splits - most likely detector bugs"
            elif abs(p - f) == 1:
                interp = "Moderate inconsistency"
            elif min(p, f) == 1:
                interp = "Strong disagreement (likely real model differences)"
            else:
                interp = "Moderate to strong disagreement"

            print(f"{split:<15s} {count:>6d} {interp}")

        # Show 50/50 splits in detail
        fifty_fifty = [item for item in comparison['inconsistent']
                       if item['pass_count'] == item['fail_count']]

        if fifty_fifty:
            print("\n" + "=" * 100)
            print(f"50/50 SPLITS - HIGHEST PRIORITY FOR REVIEW ({len(fifty_fifty)} tests)")
            print("-" * 100)
            print(f"{'Test ID':<35s} {'Category':<30s} {'Pass':>4s} {'Fail':>4s}")
            print("-" * 100)

            for item in sorted(fifty_fifty, key=lambda x: x['test_id'])[:30]:
                print(f"{item['test_id']:<35s} {item['category']:<30s} "
                      f"{item['pass_count']:>4d} {item['fail_count']:>4d}")

            if len(fifty_fifty) > 30:
                print(f"\n  ... and {len(fifty_fifty) - 30} more 50/50 split tests")

    print("\n" + "=" * 100)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 compare_primary_scores.py <model1.json> <model2.json> [model3.json ...]")
        sys.exit(1)

    model_results = {}
    models = []

    for file_path in sys.argv[1:]:
        if not Path(file_path).exists():
            print(f"Warning: File not found: {file_path}")
            continue

        model_name = Path(file_path).stem.replace('iteration10_', '')
        models.append(model_name)

        print(f"Loading PRIMARY scores: {model_name}")
        model_results[model_name] = load_primary_results(file_path)
        print(f"  Found {len(model_results[model_name])} tests with PRIMARY scores (max_score=2)")

    if len(model_results) < 2:
        print("Error: Need at least 2 models to compare")
        sys.exit(1)

    print(f"\nComparing PRIMARY detector scores across {len(model_results)} models...\n")
    comparison = compare_models(model_results)

    print_report(comparison, models)

    # Save to file
    output_file = "reports/iteration10_primary_comparison.json"
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2)

    print(f"✅ Detailed comparison saved to: {output_file}")

    return 0 if len(comparison['inconsistent']) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
