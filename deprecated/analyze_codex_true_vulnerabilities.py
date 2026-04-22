#!/usr/bin/env python3
"""
Analyze codex-app-security-skill to separate actual vulnerabilities from refusals
"""
import json
from collections import defaultdict

with open('reports/codex-app-security-skill_analysis.json', 'r') as f:
    data = json.load(f)

# Categorize all results
secure = []
vulnerable = []
refused = []

for result in data['detailed_results']:
    score = result.get('score', 2)
    vulns = result.get('vulnerabilities', [])

    # Check if UNSUPPORTED
    is_unsupported = False
    for v in vulns:
        if isinstance(v, dict):
            if v.get('type') == 'UNSUPPORTED':
                is_unsupported = True
                break
        elif 'UNSUPPORTED' in str(v):
            is_unsupported = True
            break

    if score == 2:
        secure.append(result)
    elif score == 0 and is_unsupported:
        refused.append(result)
    elif score == 0:
        vulnerable.append(result)

print('CODEX-APP-SECURITY-SKILL: True Vulnerability Analysis')
print('='*80)
print(f'Total Test Cases: 760')
print()
print(f'✅ SECURE (generated safe code):        {len(secure):3} ({len(secure)/760*100:.1f}%)')
print(f'❌ VULNERABLE (exploitable code):       {len(vulnerable):3} ({len(vulnerable)/760*100:.1f}%)')
print(f'🚫 REFUSED (no code generated):         {len(refused):3} ({len(refused)/760*100:.1f}%)')
print('='*80)
print()
print(f'TRUE VULNERABILITY RATE: {len(vulnerable)}/760 = {len(vulnerable)/760*100:.1f}%')
print(f'(Original report incorrectly counted REFUSED as vulnerable: {(len(vulnerable)+len(refused))/760*100:.1f}%)')
print()

# Detailed breakdown of TRUE vulnerabilities (not refusals)
print('\n' + '='*80)
print(f'50 TRUE EXPLOITABLE VULNERABILITIES')
print('='*80)

# Group by category
by_category = defaultdict(list)
for vuln in vulnerable:
    by_category[vuln['category']].append(vuln)

# Sort categories by count
sorted_categories = sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)

count = 1
for category, vulns in sorted_categories:
    cat_name = category.upper().replace('_', ' ')
    print(f'\n{cat_name} ({len(vulns)} vulnerabilities)')
    print('-'*80)
    for vuln in vulns:
        # Extract vulnerability types
        vuln_types = []
        for v in vuln.get('vulnerabilities', []):
            if isinstance(v, dict):
                vuln_types.append(v.get('type', str(v)))
            else:
                vuln_types.append(str(v))

        vulns_str = ', '.join(vuln_types) if vuln_types else 'Generic vulnerability'
        print(f'  {count:3}. {vuln["prompt_id"]:<40} [{vuln["language"]:10}]')
        if vuln_types:
            print(f'       {vulns_str}')
        count += 1

print(f'\n{"="*80}')
print(f'SUMMARY:')
print(f'  - Actual exploitable code generated: {len(vulnerable)} cases')
print(f'  - Secure code generated: {len(secure)} cases')
print(f'  - Refused to generate code: {len(refused)} cases')
print(f'\nSecurity Score (excluding refusals): {len(secure)}/{len(secure)+len(vulnerable)} = {len(secure)/(len(secure)+len(vulnerable))*100:.1f}%')
print(f'Task Completion Rate: {(len(secure)+len(vulnerable))/760*100:.1f}%')
