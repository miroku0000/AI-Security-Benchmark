#!/usr/bin/env python3
"""
Extract tests with 2-4 and 4-2 split patterns from Iteration 11 results.
- 2-4 split: 2 models PASS, 4 models FAIL
- 4-2 split: 4 models PASS, 2 models FAIL
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
    """Extract tests with 2-4 and 4-2 split patterns."""
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
    splits_24 = []  # 2 PASS, 4 FAIL
    splits_42 = []  # 4 PASS, 2 FAIL

    for test_id, model_results in test_index.items():
        # Only analyze if we have results from all 6 models (or 5-6 for cursor edge case)
        if len(model_results) < 5:
            continue

        pass_count = sum(1 for r in model_results.values() if r['verdict'] == 'PASS')
        fail_count = sum(1 for r in model_results.values() if r['verdict'] == 'FAIL')

        # Get category from any model
        category = next(iter(model_results.values()))['category']

        if pass_count == 2 and fail_count == 4:
            splits_24.append({
                'test_id': test_id,
                'category': category,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'models': model_results
            })
        elif pass_count == 4 and fail_count == 2:
            splits_42.append({
                'test_id': test_id,
                'category': category,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'models': model_results
            })

    return splits_24, splits_42

def sample_tests(splits_24, splits_42, sample_size=10):
    """Sample tests from both split categories."""
    total = len(splits_24) + len(splits_42)

    # Proportional sampling
    n_24 = int(sample_size * len(splits_24) / total) if total > 0 else 0
    n_42 = sample_size - n_24

    # Ensure we don't sample more than available
    n_24 = min(n_24, len(splits_24))
    n_42 = min(n_42, len(splits_42))

    sample_24 = random.sample(splits_24, n_24) if n_24 > 0 else []
    sample_42 = random.sample(splits_42, n_42) if n_42 > 0 else []

    return sample_24, sample_42

def main():
    print("="*80)
    print("ITERATION 12: EXTRACT 2-4 AND 4-2 SPLIT TESTS")
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
    print("Extracting 2-4 and 4-2 split tests...")
    splits_24, splits_42 = extract_splits(all_results)

    print(f"✅ Found {len(splits_24)} tests with 2-4 split (2 PASS, 4 FAIL)")
    print(f"✅ Found {len(splits_42)} tests with 4-2 split (4 PASS, 2 FAIL)")
    print(f"   Total: {len(splits_24) + len(splits_42)} tests")
    print()

    # Sample tests
    print("Sampling 10 tests for manual review...")
    sample_24, sample_42 = sample_tests(splits_24, splits_42, sample_size=10)

    print(f"  • {len(sample_24)} from 2-4 splits")
    print(f"  • {len(sample_42)} from 4-2 splits")
    print()

    # Combine samples
    all_samples = sample_24 + sample_42

    # Save to JSON
    output_path = 'reports/iteration12_sample_tests.json'
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
        print(f"   ✅ PASS: {', '.join(pass_models)}")
        print(f"   ❌ FAIL: {', '.join(fail_models)}")

    print()
    print("="*80)
    print("Next step: Run scripts/analyze_fifty_fifty_sample.py to review these tests")
    print("="*80)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
