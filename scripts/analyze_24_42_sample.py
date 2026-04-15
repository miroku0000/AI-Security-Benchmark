#!/usr/bin/env python3
"""
Analyze 2-4 and 4-2 split tests to classify as:
1. FALSE POSITIVE: Detector incorrectly flags secure code
2. FALSE NEGATIVE: Detector misses vulnerable code
3. CORRECT SPLIT: Real differences in model security capabilities
"""

import json
import sys
from pathlib import Path

def load_sample():
    """Load the sampled 2-4 and 4-2 split tests."""
    with open('reports/iteration12_sample_tests.json', 'r') as f:
        return json.load(f)

def analyze_test(test_info):
    """Analyze a single test by reading generated code from models."""
    test_id = test_info['test_id']
    category = test_info['category']

    print(f"\n{'='*80}")
    print(f"TEST: {test_id} [{category}]")
    print(f"{'='*80}")

    # Get PASS and FAIL models
    pass_models = [m for m, v in test_info['models'].items()
                   if v['verdict'] == 'PASS']
    fail_models = [m for m, v in test_info['models'].items()
                   if v['verdict'] == 'FAIL']

    split_type = f"{len(pass_models)}-{len(fail_models)}"
    print(f"\nSplit: {split_type}")
    print(f"✅ PASS ({len(pass_models)}): {', '.join(pass_models)}")
    print(f"❌ FAIL ({len(fail_models)}): {', '.join(fail_models)}")

    # Find the test file
    model_dirs = [
        'claude-opus-4-6_temp0.0',
        'claude-sonnet-4-5',
        'gpt-4o',
        'gpt-5.4',
        'deepseek-coder',
        'cursor'
    ]

    # Try to find file extension
    test_files = []
    for model_dir in model_dirs:
        model_path = Path(f'output/{model_dir}')
        if model_path.exists():
            # Try common extensions
            for ext in ['.py', '.js', '.java', '.go', '.rs', '.cpp', '.cs', '.tf', '.yaml', '.yml', '.swift', '.kt', '.proto', '.graphql']:
                test_file = model_path / f"{test_id}{ext}"
                if test_file.exists():
                    test_files.append((model_dir, test_file))
                    break

    if not test_files:
        print(f"\n⚠️  No files found for {test_id}")
        return None

    # Read first few lines from one PASS and one FAIL model
    pass_example = None
    fail_example = None

    for model_dir, test_file in test_files:
        model_name = model_dir.replace('_temp0.0', '')
        if model_name in pass_models and not pass_example:
            pass_example = (model_name, test_file)
        elif model_name in fail_models and not fail_example:
            fail_example = (model_name, test_file)

    # Show file sizes as a quick proxy for complexity
    print(f"\n📊 File Sizes:")
    pass_sizes = []
    fail_sizes = []

    for model_dir, test_file in test_files:
        model_name = model_dir.replace('_temp0.0', '')
        size = test_file.stat().st_size
        verdict = "✅" if model_name in pass_models else "❌"
        print(f"  {verdict} {model_name}: {size} bytes")

        if model_name in pass_models:
            pass_sizes.append(size)
        else:
            fail_sizes.append(size)

    # Show average sizes
    if pass_sizes and fail_sizes:
        avg_pass = sum(pass_sizes) / len(pass_sizes)
        avg_fail = sum(fail_sizes) / len(fail_sizes)
        print(f"\n  Average PASS: {avg_pass:.0f} bytes")
        print(f"  Average FAIL: {avg_fail:.0f} bytes")
        if avg_pass > avg_fail * 1.5:
            print(f"  📈 PASS models are significantly larger ({avg_pass/avg_fail:.1f}x)")
        elif avg_fail > avg_pass * 1.5:
            print(f"  📉 FAIL models are significantly larger ({avg_fail/avg_pass:.1f}x)")

    # Show snippet from one PASS and one FAIL for comparison
    if pass_example:
        model_name, test_file = pass_example
        print(f"\n✅ PASS Example ({model_name}) - First 30 lines:")
        print("-" * 80)
        with open(test_file, 'r') as f:
            lines = f.readlines()[:30]
            for i, line in enumerate(lines, 1):
                print(f"{i:3d} {line}", end='')

    if fail_example:
        model_name, test_file = fail_example
        print(f"\n\n❌ FAIL Example ({model_name}) - First 30 lines:")
        print("-" * 80)
        with open(test_file, 'r') as f:
            lines = f.readlines()[:30]
            for i, line in enumerate(lines, 1):
                print(f"{i:3d} {line}", end='')

    print("\n\n" + "="*80)
    print("MANUAL CLASSIFICATION NEEDED:")
    print("1. FALSE POSITIVE - Detector incorrectly flags secure code")
    print("2. FALSE NEGATIVE - Detector misses vulnerable code")
    print("3. CORRECT SPLIT - Real model security differences")
    print("="*80)

    return {
        'test_id': test_id,
        'category': category,
        'split_type': split_type,
        'pass_models': pass_models,
        'fail_models': fail_models,
        'file_sizes': {model_dir.replace('_temp0.0', ''): test_file.stat().st_size
                      for model_dir, test_file in test_files}
    }


def main():
    sample = load_sample()

    print("="*80)
    print("ITERATION 12: MANUAL REVIEW OF 2-4 AND 4-2 SPLIT TESTS")
    print("="*80)
    print(f"\nAnalyzing {len(sample)} sampled tests...\n")

    # Count split types
    splits_24 = [t for t in sample if t['pass_count'] == 2]
    splits_42 = [t for t in sample if t['pass_count'] == 4]

    print(f"Sample breakdown:")
    print(f"  • 2-4 splits: {len(splits_24)} tests")
    print(f"  • 4-2 splits: {len(splits_42)} tests")

    results = []
    for i, test_info in enumerate(sample, 1):
        print(f"\n\n{'#'*80}")
        print(f"# TEST {i}/{len(sample)}")
        print(f"{'#'*80}")

        result = analyze_test(test_info)
        if result:
            results.append(result)

        # Pause for review after each test
        if i < len(sample):
            input("\n\nPress Enter to continue to next test...")

    # Save analysis
    with open('reports/iteration12_manual_review.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\n✅ Analysis saved to reports/iteration12_manual_review.json")
    print(f"Analyzed {len(results)} tests")
    print("\nNext step: Review each test and classify as FALSE_POSITIVE, FALSE_NEGATIVE, or CORRECT_SPLIT")
    print("Document classifications in reports/iteration12_classifications.md")


if __name__ == '__main__':
    sys.exit(main())
