#!/usr/bin/env python3
"""
Quick analysis of batch 2 sampled tests to identify potential detector bugs.
"""

import json

# Load batch 2 sample
with open('reports/iteration13_batch2_sample_tests.json', 'r') as f:
    sample = json.load(f)

# Load all model reports
models = {
    'claude-opus-4-6': 'reports/iteration11_claude-opus-4-6.json',
    'claude-sonnet-4-5': 'reports/iteration11_claude-sonnet-4-5.json',
    'gpt-4o': 'reports/iteration11_gpt-4o.json',
    'gpt-5.4': 'reports/iteration11_gpt-5.4.json',
    'deepseek-coder': 'reports/iteration11_deepseek-coder.json',
    'cursor': 'reports/iteration11_cursor.json'
}

reports = {}
for model, path in models.items():
    with open(path, 'r') as f:
        data = json.load(f)
        reports[model] = {test['prompt_id']: test for test in data['detailed_results']}

print("="*80)
print("ITERATION 13 BATCH 2: QUICK ANALYSIS")
print("="*80)
print()

for i, test_info in enumerate(sample, 1):
    test_id = test_info['test_id']
    category = test_info['category']
    split = f"{test_info['pass_count']}-{test_info['fail_count']}"

    print(f"\n{i}. {test_id} [{category}] - Split: {split}")
    print("-" * 80)

    pass_models = [m for m, v in test_info['models'].items() if v['verdict'] == 'PASS']
    fail_models = [m for m, v in test_info['models'].items() if v['verdict'] == 'FAIL']

    if len(pass_models) == 1:
        print(f"✅ ONLY PASS: {pass_models[0]}")
        print(f"❌ ALL FAIL: {', '.join(fail_models)}")
    else:
        print(f"✅ ALL PASS: {', '.join(pass_models)}")
        print(f"❌ ONLY FAIL: {fail_models[0]}")
    print()

    # Show vulnerabilities by model
    print("Vulnerability Summary:")
    for model in models:
        if test_id in reports[model]:
            test = reports[model][test_id]
            vulns = test.get('vulnerabilities', [])
            score = test.get('primary_detector_score', 0)
            verdict = "✅" if model in pass_models else "❌"

            if vulns:
                # Group by severity
                critical = [v for v in vulns if v.get('severity') == 'CRITICAL']
                high = [v for v in vulns if v.get('severity') == 'HIGH']
                medium = [v for v in vulns if v.get('severity') == 'MEDIUM']
                low = [v for v in vulns if v.get('severity') == 'LOW']

                vuln_str = []
                if critical:
                    vuln_str.append(f"{len(critical)} CRITICAL")
                if high:
                    vuln_str.append(f"{len(high)} HIGH")
                if medium:
                    vuln_str.append(f"{len(medium)} MEDIUM")
                if low:
                    vuln_str.append(f"{len(low)} LOW")

                print(f"  {verdict} {model:20s} Score: {score}/2  {', '.join(vuln_str)}")

                # Show first vuln type
                if vulns:
                    v = vulns[0]
                    print(f"      → {v['type']} ({v['severity']})")
            else:
                print(f"  {verdict} {model:20s} Score: {score}/2  SECURE (no vulnerabilities)")

print("\n" + "="*80)
print("Analysis complete - reviewing for detector bugs...")
print("="*80)
