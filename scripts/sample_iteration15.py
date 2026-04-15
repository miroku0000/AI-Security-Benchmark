#!/usr/bin/env python3
"""
Iteration 15: Sample 20 new tests for high-end validation.
Uses different random seed (2027) to get different sample than Iteration 14.
"""

import json
import random
from collections import defaultdict

def load_iteration11_results():
    """Load Iteration 11 results for all 6 models."""
    models = ['claude-opus-4-6', 'claude-sonnet-4-5', 'gpt-4o', 'gpt-5.4', 'deepseek-coder', 'cursor']

    all_results = {}
    for model in models:
        report_path = f'reports/iteration11_{model}.json'
        try:
            with open(report_path, 'r') as f:
                data = json.load(f)
                all_results[model] = {
                    'results': data['detailed_results'],
                    'by_id': {test['prompt_id']: test for test in data['detailed_results']}
                }
                print(f"✅ Loaded {model}: {len(data['detailed_results'])} tests")
        except FileNotFoundError:
            print(f"⚠️  Report not found: {report_path}")

    return all_results

def categorize_tests(all_results):
    """Categorize tests by verdict patterns."""
    test_index = defaultdict(dict)

    for model, data in all_results.items():
        for test in data['results']:
            test_id = test['prompt_id']
            if test.get('primary_detector_max_score') == 2:
                test_index[test_id][model] = {
                    'verdict': test.get('primary_detector_result', 'UNKNOWN'),
                    'score': test.get('primary_detector_score', 0),
                    'category': test.get('category', 'unknown'),
                    'vulnerabilities': test.get('vulnerabilities', [])
                }

    unanimous_pass = []
    unanimous_fail = []
    split_verdicts = []

    for test_id, model_results in test_index.items():
        if len(model_results) < 6:
            continue

        pass_count = sum(1 for r in model_results.values() if r['verdict'] == 'PASS')
        fail_count = sum(1 for r in model_results.values() if r['verdict'] == 'FAIL')

        if pass_count == 6:
            unanimous_pass.append({
                'test_id': test_id,
                'category': next(iter(model_results.values()))['category'],
                'models': model_results
            })
        elif fail_count == 6:
            unanimous_fail.append({
                'test_id': test_id,
                'category': next(iter(model_results.values()))['category'],
                'models': model_results
            })
        else:
            split_verdicts.append({
                'test_id': test_id,
                'category': next(iter(model_results.values()))['category'],
                'pass_count': pass_count,
                'fail_count': fail_count,
                'models': model_results
            })

    return {
        'unanimous_pass': unanimous_pass,
        'unanimous_fail': unanimous_fail,
        'split_verdicts': split_verdicts
    }

def sample_for_validation(categorized, sample_size=20):
    """Sample tests for high-end model validation."""
    n_pass = int(sample_size * 0.4)
    n_fail = int(sample_size * 0.4)
    n_split = sample_size - n_pass - n_fail

    sample_pass = random.sample(categorized['unanimous_pass'], min(n_pass, len(categorized['unanimous_pass'])))
    sample_fail = random.sample(categorized['unanimous_fail'], min(n_fail, len(categorized['unanimous_fail'])))
    sample_split = random.sample(categorized['split_verdicts'], min(n_split, len(categorized['split_verdicts'])))

    return {
        'unanimous_pass': sample_pass,
        'unanimous_fail': sample_fail,
        'split_verdicts': sample_split,
        'all': sample_pass + sample_fail + sample_split
    }

def main():
    print("=" * 80)
    print("ITERATION 15: HIGH-END VALIDATION SAMPLING")
    print("Using different random seed (2027) for new sample")
    print("=" * 80)
    print()

    # Set different seed for Iteration 15
    random.seed(2027)

    # Load results
    print("Loading Iteration 11 validation results...")
    all_results = load_iteration11_results()
    print()

    if len(all_results) < 6:
        print("❌ Need all 6 models to analyze")
        return 1

    # Categorize tests
    print("Categorizing tests by verdict patterns...")
    categorized = categorize_tests(all_results)

    print(f"✅ Found {len(categorized['unanimous_pass'])} tests with unanimous PASS (6-0)")
    print(f"✅ Found {len(categorized['unanimous_fail'])} tests with unanimous FAIL (0-6)")
    print(f"✅ Found {len(categorized['split_verdicts'])} tests with split verdicts")
    print()

    # Sample tests for validation
    print("Sampling 20 tests for Iteration 15...")
    samples = sample_for_validation(categorized, sample_size=20)

    print(f"  • {len(samples['unanimous_pass'])} unanimous PASS (check for false negatives)")
    print(f"  • {len(samples['unanimous_fail'])} unanimous FAIL (check for false positives)")
    print(f"  • {len(samples['split_verdicts'])} split verdicts (validate previous findings)")
    print()

    # Save sample metadata
    output_path = 'reports/iteration15_high_end_validation_sample.json'
    with open(output_path, 'w') as f:
        json.dump(samples['all'], f, indent=2)

    print(f"✅ Saved sample metadata to {output_path}")
    print()

    # Print summary
    print("=" * 80)
    print("ITERATION 15 SAMPLE SUMMARY")
    print("=" * 80)
    print()

    for i, test in enumerate(samples['all'], 1):
        test_id = test['test_id']
        category = test['category']

        if 'pass_count' in test:
            split = f"{test['pass_count']}-{test['fail_count']}"
            verdict_type = "SPLIT"
        else:
            pass_count = sum(1 for r in test['models'].values() if r['verdict'] == 'PASS')
            if pass_count == 6:
                split = "6-0"
                verdict_type = "UNANIMOUS PASS"
            else:
                split = "0-6"
                verdict_type = "UNANIMOUS FAIL"

        print(f"{i}. {test_id} [{category}]")
        print(f"   Verdict Pattern: {verdict_type} ({split})")

        # Show example from gpt-4o
        example_model = 'gpt-4o'
        if example_model in test['models']:
            example = test['models'][example_model]
            print(f"   Example ({example_model}): {example['verdict']} - {example['score']}/2")
            if example['vulnerabilities']:
                vuln = example['vulnerabilities'][0]
                print(f"     → {vuln.get('type', 'UNKNOWN')} ({vuln.get('severity', 'UNKNOWN')}): {vuln.get('description', '')[:60]}...")
        print()

    print("=" * 80)
    print("Ready for high-end reasoning analysis")
    print("=" * 80)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
