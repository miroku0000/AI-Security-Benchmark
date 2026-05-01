#!/usr/bin/env python3
"""
Debug script to see what SAST rule IDs are actually in the test data
"""

import json
from pathlib import Path

def analyze_semgrep_results():
    """Analyze the semgrep results to see what rule IDs are present"""
    sast_file = Path("../testsast/semgrep-results-allknownbad.json")

    if not sast_file.exists():
        print(f"❌ File not found: {sast_file}")
        return

    with open(sast_file, 'r') as f:
        data = json.load(f)

    # Extract rule IDs from semgrep results
    rule_ids = set()

    if 'results' in data:
        for result in data['results']:
            if 'check_id' in result:
                rule_ids.add(result['check_id'])

    print(f"🔍 Found {len(rule_ids)} unique rule IDs in SAST data:")
    for rule_id in sorted(rule_ids):
        print(f"  - {rule_id}")

    # Show first 5 rule IDs for mapping rules creation
    print(f"\n🔧 First 5 rule IDs for creating mapping rules:")
    for rule_id in sorted(list(rule_ids)[:5]):
        print(f"  '{rule_id}',")

if __name__ == '__main__':
    analyze_semgrep_results()