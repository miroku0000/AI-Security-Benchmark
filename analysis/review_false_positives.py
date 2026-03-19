#!/usr/bin/env python3
"""
Review all 'false positives' to identify real vulnerabilities missed by benchmark
"""

import json

# Load all FPs
with open('all_false_positives_for_review.json') as f:
    all_fps = json.load(f)

# Manual classification of common patterns
KNOWN_REAL_VULNERABILITIES = {
    'B201': {'type': 'DEBUG_MODE_ENABLED', 'real': True, 'description': 'Flask debug=True in production'},
    'B105': {'type': 'HARDCODED_SECRET', 'real': True, 'description': 'Hardcoded password/key', 'needs_review': True},
    'B106': {'type': 'HARDCODED_SECRET', 'real': True, 'description': 'Hardcoded password'},
    'B107': {'type': 'HARDCODED_SECRET', 'real': True, 'description': 'Hardcoded password'},
    'B603': {'type': 'COMMAND_INJECTION', 'real': True, 'description': 'Subprocess without shell=False'},
    'B404': {'type': 'IMPORT_WARNING', 'real': False, 'description': 'Import warning only'},
    'app.opengrep-rules.python.flask.security.audit.debug-enabled': {'type': 'DEBUG_MODE_ENABLED', 'real': True, 'description': 'Flask debug mode'},
    'python.flask.security.audit.debug-enabled.debug-enabled': {'type': 'DEBUG_MODE_ENABLED', 'real': True, 'description': 'Flask debug mode'},
}

print("="*100)
print("SYSTEMATIC REVIEW OF ALL 'FALSE POSITIVES'")
print("="*100)
print()

# Categorize
real_vulns = []
likely_fps = []
needs_review = []

for fp in all_fps:
    rule = fp['rule_id']

    if rule in KNOWN_REAL_VULNERABILITIES:
        classification = KNOWN_REAL_VULNERABILITIES[rule]
        if classification['real']:
            if classification.get('needs_review'):
                needs_review.append({**fp, 'vuln_type': classification['type'], 'description': classification['description']})
            else:
                real_vulns.append({**fp, 'vuln_type': classification['type'], 'description': classification['description']})
        else:
            likely_fps.append({**fp, 'reason': classification['description']})
    else:
        needs_review.append({**fp, 'vuln_type': 'UNKNOWN', 'description': 'Needs manual review'})

print(f"SUMMARY:")
print(f"  Confirmed real vulnerabilities: {len(real_vulns)}")
print(f"  Likely false positives: {len(likely_fps)}")
print(f"  Needs manual review: {len(needs_review)}")
print()

print("="*100)
print("CONFIRMED REAL VULNERABILITIES (Missing from Ground Truth)")
print("="*100)
print()

from collections import defaultdict
by_file = defaultdict(list)

for vuln in real_vulns:
    by_file[vuln['filename']].append(vuln)

for filename in sorted(by_file.keys()):
    print(f"\n{filename}:")
    for vuln in by_file[filename]:
        print(f"  Line {vuln['line']:>3}: {vuln['vuln_type']:<25} ({vuln['tool']}) - {vuln['description']}")

print()
print("="*100)
print("NEEDS MANUAL REVIEW")
print("="*100)
print()

for item in needs_review[:20]:  # Show first 20
    print(f"{item['filename']}:{item['line']}")
    print(f"  Tool: {item['tool']}")
    print(f"  Rule: {item['rule_id']}")
    print(f"  Title: {item['title'][:80]}")
    print()

if len(needs_review) > 20:
    print(f"... and {len(needs_review) - 20} more items needing review")

print()
print("="*100)
print("LIKELY FALSE POSITIVES")
print("="*100)
print()

for item in likely_fps:
    print(f"{item['filename']}:{item['line']} - {item['rule_id'][:50]}")
    print(f"  Reason: {item['reason']}")
    print()

# Generate summary for ground truth updates
print()
print("="*100)
print("GROUND TRUTH UPDATE SUMMARY")
print("="*100)
print()

vuln_types = defaultdict(int)
for vuln in real_vulns:
    vuln_types[vuln['vuln_type']] += 1

print("Vulnerability types to add to benchmark:")
for vtype, count in sorted(vuln_types.items(), key=lambda x: x[1], reverse=True):
    print(f"  • {vtype}: {count} instances")

print()
print(f"Total files needing ground truth updates: {len(by_file)}")

# Save results
output = {
    'confirmed_real_vulnerabilities': real_vulns,
    'needs_manual_review': needs_review,
    'likely_false_positives': likely_fps,
    'summary': {
        'real_vulns_count': len(real_vulns),
        'needs_review_count': len(needs_review),
        'likely_fps_count': len(likely_fps),
        'files_to_update': list(by_file.keys())
    }
}

with open('fp_review_results.json', 'w') as f:
    json.dump(output, f, indent=2)

print()
print("Detailed results saved to: fp_review_results.json")
