#!/usr/bin/env python3
"""
Analyze prompts from ID 160 onwards and check for detector mappings.
Per user request: assess all prompts from 160 on and ensure they have detectors written.
"""

import yaml
import json
from collections import defaultdict

def load_all_prompts():
    """Load prompts from all YAML files."""
    all_prompts = []
    prompt_files = [
        'prompts/prompts.yaml',
        'prompts/prompts_level1_security.yaml',
        'prompts/prompts_level2_security.yaml',
        'prompts/prompts_level3_security.yaml',
        'prompts/prompts_level4_security.yaml',
        'prompts/prompts_level5_security.yaml',
    ]

    for file_path in prompt_files:
        try:
            with open(file_path, 'r') as f:
                prompts = yaml.safe_load(f)
                if prompts:
                    all_prompts.extend(prompts)
                    print(f"Loaded {len(prompts)} prompts from {file_path}")
        except FileNotFoundError:
            print(f"Warning: {file_path} not found, skipping...")

    return all_prompts

def extract_prompt_number(prompt_id):
    """Extract numeric ID from prompt ID like 'mobile_020' -> 20."""
    if not prompt_id or not isinstance(prompt_id, str):
        return 0

    parts = prompt_id.split('_')
    if len(parts) >= 2:
        try:
            return int(parts[-1])
        except ValueError:
            return 0
    return 0

def load_runner_mappings():
    """Extract category mappings from runner.py."""
    with open('runner.py', 'r') as f:
        content = f.read()

    # Extract mapped categories
    import re
    # Find all category mappings in runner.py
    pattern = r"'([^']+)':\s*(\w+Detector)"
    matches = re.findall(pattern, content)

    mapped = {category: detector for category, detector in matches}
    return mapped

def main():
    print("=" * 80)
    print("ANALYZING HIGH-ID PROMPTS (ID >= 160)")
    print("=" * 80)
    print()

    # Load all prompts
    all_prompts = load_all_prompts()
    print(f"\nTotal prompts loaded: {len(all_prompts)}")

    # Filter prompts with ID >= 160
    high_id_prompts = []
    for p in all_prompts:
        prompt_id = p.get('id', '')
        num_id = extract_prompt_number(prompt_id)
        if num_id >= 160:
            high_id_prompts.append(p)

    print(f"Prompts with numeric ID >= 160: {len(high_id_prompts)}")
    print()

    # Group by category
    categories = defaultdict(list)
    for p in high_id_prompts:
        category = p.get('category', 'UNKNOWN')
        categories[category].append(p)

    print(f"Unique categories in ID >= 160: {len(categories)}")
    print()

    # Load runner mappings
    print("Loading detector mappings from runner.py...")
    runner_mappings = load_runner_mappings()
    print(f"Total mapped categories in runner.py: {len(runner_mappings)}")
    print()

    # Analyze coverage
    print("=" * 80)
    print("CATEGORIES IN HIGH-ID PROMPTS (ID >= 160)")
    print("=" * 80)
    print()

    missing_detectors = []
    has_detectors = []

    for category in sorted(categories.keys()):
        prompts = categories[category]
        count = len(prompts)
        has_detector = category in runner_mappings
        detector_name = runner_mappings.get(category, "NO DETECTOR")

        status = "✅" if has_detector else "❌"
        print(f"{status} {category}: {count} prompts → {detector_name}")

        if has_detector:
            has_detectors.append((category, count, detector_name))
        else:
            missing_detectors.append((category, count))

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Categories with detectors: {len(has_detectors)}")
    print(f"Categories WITHOUT detectors: {len(missing_detectors)}")
    print(f"Total prompts affected by missing detectors: {sum(count for _, count in missing_detectors)}")
    print()

    if missing_detectors:
        print("=" * 80)
        print("MISSING DETECTORS (HIGH PRIORITY)")
        print("=" * 80)
        print()
        for category, count in sorted(missing_detectors, key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count} prompts")
            # Show sample prompt IDs
            sample_ids = [p['id'] for p in categories[category][:3]]
            print(f"    Sample IDs: {', '.join(sample_ids)}")
        print()

    # Save detailed report
    report = {
        'total_prompts': len(all_prompts),
        'high_id_prompts': len(high_id_prompts),
        'unique_categories': len(categories),
        'categories_with_detectors': len(has_detectors),
        'categories_without_detectors': len(missing_detectors),
        'total_prompts_missing_detectors': sum(count for _, count in missing_detectors),
        'missing_categories': [
            {
                'category': cat,
                'prompt_count': count,
                'sample_prompts': [p['id'] for p in categories[cat][:5]]
            }
            for cat, count in missing_detectors
        ],
        'mapped_categories': [
            {
                'category': cat,
                'prompt_count': count,
                'detector': detector
            }
            for cat, count, detector in has_detectors
        ]
    }

    output_path = 'reports/high_id_prompts_analysis.json'
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"✅ Detailed report saved to {output_path}")
    print()

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
