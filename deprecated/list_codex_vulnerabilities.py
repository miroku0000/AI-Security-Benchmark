#!/usr/bin/env python3
"""
List all exploitable vulnerabilities found in codex-app-security-skill
"""
import json
from collections import defaultdict

with open('reports/codex-app-security-skill_analysis.json', 'r') as f:
    data = json.load(f)

# Get vulnerable categories
vuln_categories = {}
for cat_name, cat_data in data['categories'].items():
    if cat_data.get('vulnerable', 0) > 0:
        vuln_categories[cat_name] = cat_data.get('vulnerable', 0)

# Find all tests in vulnerable categories and check their scores
vulnerable_tests = []
for result in data['detailed_results']:
    category = result.get('category', '')
    if category in vuln_categories:
        score = result.get('score', 2)
        # Score of 0 = vulnerable
        if score == 0:
            # Handle vulnerabilities - could be list of strings or list of dicts
            vulns_raw = result.get('vulnerabilities', [])
            vulns = []
            for v in vulns_raw:
                if isinstance(v, dict):
                    vulns.append(v.get('type', str(v)))
                else:
                    vulns.append(str(v))

            vulnerable_tests.append({
                'id': result['prompt_id'],
                'category': category,
                'language': result['language'],
                'vulnerabilities': vulns,
            })

print(f'CODEX-APP-SECURITY-SKILL: Exploitable Vulnerabilities Found')
print(f'Total: {len(vulnerable_tests)} out of 760 test cases (12.8%)')
print('='*80)
print()

# Group by category
by_category = defaultdict(list)
for test in vulnerable_tests:
    by_category[test['category']].append(test)

# Sort categories by count
sorted_categories = sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)

count = 1
for category, tests in sorted_categories:
    cat_name = category.upper().replace('_', ' ')
    print(f'\n{cat_name} ({len(tests)} vulnerabilities)')
    print('-'*80)
    for test in tests:
        vulns_str = ', '.join(test['vulnerabilities']) if test['vulnerabilities'] else 'Generic vulnerability'
        print(f'  {count:3}. {test["id"]:<40} [{test["language"]:10}]')
        if test['vulnerabilities']:
            print(f'       {vulns_str}')
        count += 1

print(f'\n{"="*80}')
print(f'Total: {len(vulnerable_tests)} exploitable vulnerabilities')
