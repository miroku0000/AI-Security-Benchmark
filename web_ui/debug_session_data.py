#!/usr/bin/env python3
"""
Debug script to examine actual session data and understand why mapping rules aren't matching
"""

import requests
import json
from collections import defaultdict

def analyze_session_data():
    """Analyze session data to understand SAST and benchmark vulnerability types"""
    base_url = "http://localhost:5001"
    session = requests.Session()

    print("🔍 Analyzing session data for mapping rules debugging...")

    # Get CSRF token and create session
    csrf_response = session.get(f"{base_url}/api/csrf-token")
    csrf_token = csrf_response.json()["csrf_token"]

    # Upload files to create session
    benchmark_file_path = "../testsast/reports.json"
    sast_file_path = "../testsast/semgrep-results-allknownbad.json"

    files = {
        'benchmark_file': ('reports.json', open(benchmark_file_path, 'rb'), 'application/json'),
        'sast_file': ('semgrep-results-allknownbad.json', open(sast_file_path, 'rb'), 'application/json')
    }
    data = {
        'format': 'semgrep',
        'csrf_token': csrf_token
    }

    response = session.post(f"{base_url}/api/upload", files=files, data=data)
    for file_obj in files.values():
        file_obj[1].close()

    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code}")
        return

    session_id = response.json()['session_id']
    print(f"✅ Created session: {session_id}")

    # Get session data
    session_response = session.get(f"{base_url}/api/session/{session_id}")
    session_data = session_response.json()

    print(f"📊 Session has {len(session_data['files'])} files")

    # Analyze SAST and benchmark vulnerability types
    sast_types = defaultdict(int)
    benchmark_types = defaultdict(int)
    file_matches = defaultdict(lambda: {'sast': set(), 'benchmark': set()})

    for file_data in session_data['files']:
        file_path = file_data['file_path']

        # Count SAST vulnerability types
        for sast_vuln in file_data.get('sast_vulns', []):
            # Extract vuln_type from the full vulnerability data
            if 'vuln_type' in sast_vuln:
                vuln_type = sast_vuln['vuln_type']
                sast_types[vuln_type] += 1
                file_matches[file_path]['sast'].add(vuln_type)

        # Count benchmark vulnerability types
        for bench_vuln in file_data.get('benchmark_vulns', []):
            if 'vuln_type' in bench_vuln:
                vuln_type = bench_vuln['vuln_type']
                benchmark_types[vuln_type] += 1
                file_matches[file_path]['benchmark'].add(vuln_type)

    print("\n🎯 SAST Vulnerability Types (top 10):")
    for vuln_type, count in sorted(sast_types.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {count:3d} × {vuln_type}")

    print("\n🎯 Benchmark Vulnerability Types (top 10):")
    for vuln_type, count in sorted(benchmark_types.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {count:3d} × {vuln_type}")

    # Find files that have both SAST and benchmark vulnerabilities
    print("\n🔍 Files with both SAST and benchmark vulnerabilities (first 5):")
    files_with_both = [(f, data) for f, data in file_matches.items()
                       if data['sast'] and data['benchmark']]

    for file_path, data in files_with_both[:5]:
        print(f"\n📁 {file_path}")
        print(f"   SAST types: {list(data['sast'])[:3]}...")
        print(f"   Benchmark types: {list(data['benchmark'])[:3]}...")

    # Create a mapping rule that should work
    print("\n🛠️  Suggested mapping rule:")
    if sast_types and benchmark_types:
        # Take most common SAST type and most common benchmark type
        top_sast = max(sast_types.items(), key=lambda x: x[1])
        top_benchmark = max(benchmark_types.items(), key=lambda x: x[1])

        suggested_rule = {
            "mapping_rules": {
                top_sast[0]: {
                    "benchmark_type": top_benchmark[0],
                    "confidence": 90,
                    "source": "debug_analysis"
                }
            }
        }

        print(f"   SAST rule: {top_sast[0]} ({top_sast[1]} occurrences)")
        print(f"   → Benchmark: {top_benchmark[0]} ({top_benchmark[1]} occurrences)")
        print(f"   JSON: {json.dumps(suggested_rule, indent=2)}")

        # Check if they appear in the same files
        common_files = 0
        for file_path, data in file_matches.items():
            if top_sast[0] in data['sast'] and top_benchmark[0] in data['benchmark']:
                common_files += 1

        print(f"   Files with both types: {common_files}")

if __name__ == '__main__':
    analyze_session_data()