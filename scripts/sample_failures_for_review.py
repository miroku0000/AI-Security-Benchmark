#!/usr/bin/env python3
"""
Sample failures for manual review - finds diverse false negative candidates.

Usage:
    python3 scripts/sample_failures_for_review.py reports/claude-sonnet-4-5_analysis_fixed.json
"""

import json
import random
import sys
from pathlib import Path
from collections import defaultdict

def sample_failures_by_category(analysis_file: Path, samples_per_category: int = 5):
    """Sample N failures from each category for manual review."""

    with open(analysis_file, 'r') as f:
        data = json.load(f)

    results = data.get('detailed_results', [])

    # Group failures by category
    failures_by_category = defaultdict(list)
    for r in results:
        if r.get('primary_detector_result') == 'FAIL':
            failures_by_category[r['category']].append(r)

    print(f"{'='*80}")
    print(f"FAILURE SAMPLING FOR MANUAL REVIEW")
    print(f"{'='*80}\n")
    print(f"Source: {analysis_file}")
    print(f"Total failures: {sum(len(f) for f in failures_by_category.values())}")
    print(f"Categories: {len(failures_by_category)}")
    print(f"Sample size per category: {samples_per_category}\n")

    # Sample from each category
    all_samples = []
    for category in sorted(failures_by_category.keys()):
        failures = failures_by_category[category]
        sample_size = min(samples_per_category, len(failures))
        samples = random.sample(failures, sample_size)

        all_samples.extend(samples)

        print(f"{category:30s} | {len(failures):3d} failures | Sampled: {sample_size}")

        for s in samples:
            score = s.get('primary_detector_score', 0)
            max_score = s.get('primary_detector_max_score', 2)
            code_path = s.get('generated_code_path', 'N/A')
            print(f"  - {s['prompt_id']:20s} | Score: {score}/{max_score} | {code_path}")

        print()

    # Save sample IDs to file
    output_file = Path('reports/refinement/next_review_sample.txt')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        f.write(f"# Failure Sample for Manual Review\n")
        f.write(f"# Generated from: {analysis_file}\n")
        f.write(f"# Total sampled: {len(all_samples)}\n\n")

        for category in sorted(failures_by_category.keys()):
            cat_samples = [s for s in all_samples if s['category'] == category]
            if cat_samples:
                f.write(f"\n## {category} ({len(cat_samples)} samples)\n\n")
                for s in cat_samples:
                    f.write(f"- {s['prompt_id']:20s} | {s.get('generated_code_path', 'N/A')}\n")

    print(f"{'='*80}")
    print(f"Sample saved to: {output_file}")
    print(f"Total tests to review: {len(all_samples)}")
    print(f"\nNext steps:")
    print(f"  1. Review each sampled file manually")
    print(f"  2. Identify false negatives (code is secure but detector failed)")
    print(f"  3. Document patterns in reports/refinement/")
    print(f"  4. Implement detector fixes")
    print(f"{'='*80}")

    return all_samples

def sample_edge_cases(analysis_file: Path):
    """Find tests with scores exactly at pass/fail threshold."""

    with open(analysis_file, 'r') as f:
        data = json.load(f)

    results = data.get('detailed_results', [])

    edge_cases = []
    for r in results:
        score = r.get('primary_detector_score', 0)
        max_score = r.get('primary_detector_max_score', 2)

        # Check if exactly at threshold
        if score == max_score / 2:
            edge_cases.append(r)

    print(f"\n{'='*80}")
    print(f"EDGE CASES (score exactly at threshold)")
    print(f"{'='*80}\n")

    print(f"Total edge cases: {len(edge_cases)}\n")

    for ec in edge_cases:
        result = ec.get('primary_detector_result', 'UNKNOWN')
        score = ec.get('primary_detector_score', 0)
        max_score = ec.get('primary_detector_max_score', 2)

        print(f"{ec['prompt_id']:20s} | {ec['category']:25s} | {result:4s} | {score}/{max_score}")

    return edge_cases

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/sample_failures_for_review.py <analysis_file.json>")
        sys.exit(1)

    analysis_file = Path(sys.argv[1])
    if not analysis_file.exists():
        print(f"ERROR: Analysis file not found: {analysis_file}")
        sys.exit(1)

    # Set random seed for reproducibility
    random.seed(42)

    # Sample failures by category
    samples = sample_failures_by_category(analysis_file, samples_per_category=5)

    # Also find edge cases
    edge_cases = sample_edge_cases(analysis_file)

if __name__ == '__main__':
    main()
