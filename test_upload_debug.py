#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sast_comparison import SASTComparison, Vulnerability
import json

def test_upload_process():
    try:
        # Load test data
        with open('results/test_benchmark.json', 'r') as f:
            benchmark_content = json.load(f)

        with open('results/semgrep_sql_results.json', 'r') as f:
            sast_content = json.load(f)

        print(f"Loaded benchmark: {len(benchmark_content)} items")
        print(f"Loaded SAST: {len(sast_content.get('results', []))} items")

        # Create instance like in web app
        comparison = object.__new__(SASTComparison)
        comparison.benchmark_vulns = []

        # Handle simple list format like in web app
        if isinstance(benchmark_content, list):
            from sast_comparison import Vulnerability
            for vuln_data in benchmark_content:
                comparison.benchmark_vulns.append(Vulnerability(
                    file_path=vuln_data.get('file_path', ''),
                    line_number=vuln_data.get('line_number', 0),
                    vuln_type=vuln_data.get('vuln_type', 'UNKNOWN'),
                    severity=vuln_data.get('severity', 'MEDIUM'),
                    description=vuln_data.get('description', ''),
                    source='benchmark'
                ))
        print(f"Benchmark vulns: {len(comparison.benchmark_vulns)}")

        # Parse SAST results
        sast_vulns = comparison._parse_sast_results_from_dict(sast_content, 'semgrep')
        print(f"SAST vulns: {len(sast_vulns)}")

        print("SUCCESS: Upload process works")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_upload_process()