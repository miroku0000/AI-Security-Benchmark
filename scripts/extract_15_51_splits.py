#!/usr/bin/env python3
"""
Extract tests with 1-5 and 5-1 split patterns from Iteration 11 results.
These represent extreme disagreement - most likely to contain detector edge cases.
- 1-5 split: 1 model PASS, 5 models FAIL
- 5-1 split: 5 models PASS, 1 model FAIL
"""

import json
import random
from pathlib import Path
from collections import defaultdict

def load_model_results():
    """Load Iteration 11 validation results for all 6 models."""
    models = [
        'claude-opus-4-6',
        'claude-sonnet-4-5',
        'gpt-4o',
        'gpt-5.4',
        'deepseek-coder',
        'cursor'
    ]

    all_results = {}
    for model in models:
        report_path = f'reports/iteration11_{model}.json'
        try:
            with open(report_path, 'r') as f:
                data = json.load(f)
                all_results[model] = data['detailed_results']
                print(f"✅ Loaded {model}: {len(data['detailed_results'])} tests")
        except FileNotFoundError:
            print(f"⚠️  Report not found: {report_path}")

    return all_results

def extract_splits(all_results):
    """Extract tests with 1-5 and 5-1 split patterns."""
    # Build test index: test_id -> {model: result}
    test_index = defaultdict(dict)

    for model, results in all_results.items():
        for test in results:
            test_id = test['prompt_id']

            # Only track tests with PRIMARY detector (max_score=2)
            if test.get('primary_detector_max_score') == 2:
                test_index[test_id][model] = {
                    'verdict': test.get('primary_detector_result', 'UNKNOWN'),
                    'score': test.get('primary_detector_score', 0),
                    'category': test.get('category', 'unknown')
                }

    # Classify splits
    splits_15 = []  # 1 PASS, 5 FAIL
    splits_51 = []  # 5 PASS, 1 FAIL

    for test_id, model_results in test_index.items():
        # Only analyze if we have results from all 6 models (or 5-6 for cursor edge case)
        if len(model_results) < 5:
            continue

        pass_count = sum(1 for r in model_results.values() if r['verdict'] == 'PASS')
        fail_count = sum(1 for r in model_results.values() if r['verdict'] == 'FAIL')

        # Get category from any model
        category = next(iter(model_results.values()))['category']

        if pass_count == 1 and fail_count == 5:
            splits_15.append({
                'test_id': test_id,
                'category': category,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'models': model_results
            })
        elif pass_count == 5 and fail_count == 1:
            splits_51.append({
                'test_id': test_id,
                'category': category,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'models': model_results
            })

    return splits_15, splits_51

def sample_tests(splits_15, splits_51, sample_size=10):
    """Sample tests from both split categories."""
    total = len(splits_15) + len(splits_51)

    # Proportional sampling
    n_15 = int(sample_size * len(splits_15) / total) if total > 0 else 0
    n_51 = sample_size - n_15

    # Ensure we don't sample more than available
    n_15 = min(n_15, len(splits_15))
    n_51 = min(n_51, len(splits_51))

    sample_15 = random.sample(splits_15, n_15) if n_15 > 0 else []
    sample_51 = random.sample(splits_51, n_51) if n_51 > 0 else []

    return sample_15, sample_51

def main():
    print("="*80)
    print("ITERATION 13: EXTRACT 1-5 AND 5-1 SPLIT TESTS")
    print("="*80)
    print()

    # Set random seed for reproducibility
    random.seed(42)

    # Load results
    print("Loading Iteration 11 validation results...")
    all_results = load_model_results()
    print()

    if len(all_results) < 5:
        print("❌ Need at least 5 models to analyze splits")
        return 1

    # Extract splits
    print("Extracting 1-5 and 5-1 split tests...")
    splits_15, splits_51 = extract_splits(all_results)

    print(f"✅ Found {len(splits_15)} tests with 1-5 split (1 PASS, 5 FAIL)")
    print(f"✅ Found {len(splits_51)} tests with 5-1 split (5 PASS, 1 FAIL)")
    print(f"   Total: {len(splits_15) + len(splits_51)} tests")
    print()

    # Sample tests
    print("Sampling 10 tests for manual review...")
    sample_15, sample_51 = sample_tests(splits_15, splits_51, sample_size=10)

    print(f"  • {len(sample_15)} from 1-5 splits")
    print(f"  • {len(sample_51)} from 5-1 splits")
    print()

    # Combine samples
    all_samples = sample_15 + sample_51

    # Save to JSON
    output_path = 'reports/iteration13_sample_tests.json'
    with open(output_path, 'w') as f:
        json.dump(all_samples, f, indent=2)

    print(f"✅ Saved sample to {output_path}")
    print()

    # Print summary
    print("="*80)
    print("SAMPLE SUMMARY")
    print("="*80)

    for i, test in enumerate(all_samples, 1):
        pass_models = [m for m, r in test['models'].items() if r['verdict'] == 'PASS']
        fail_models = [m for m, r in test['models'].items() if r['verdict'] == 'FAIL']

        print(f"\n{i}. {test['test_id']} [{test['category']}]")
        print(f"   Split: {test['pass_count']}-{test['fail_count']}")

        if len(pass_models) == 1:
            print(f"   ✅ ONLY PASS: {pass_models[0]}")
            print(f"   ❌ ALL FAIL: {', '.join(fail_models)}")
        else:
            print(f"   ✅ ALL PASS: {', '.join(pass_models)}")
            print(f"   ❌ ONLY FAIL: {fail_models[0]}")

    print()
    print("="*80)
    print("STRATEGY: Extreme splits (1 vs 5) are most likely to reveal:")
    print("  1. Detector bugs (false positives/negatives)")
    print("  2. Edge cases in security detection")
    print("  3. Outlier model behaviors")
    print("="*80)
    print()
    print("Next step: Analyze these tests to identify detector bugs")
    print("="*80)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
