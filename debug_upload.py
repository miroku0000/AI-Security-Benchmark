#!/usr/bin/env python3
"""
Debug script to test the exact upload process that the web UI uses
"""

import json
import requests
import os

def test_upload():
    print("🔍 Testing Web UI Upload Process")
    print("=" * 50)

    # Check if files exist
    benchmark_file = "testsast/reports.json"
    sast_file = "results/semgrep_sql_results.json"

    if not os.path.exists(benchmark_file):
        print(f"❌ Benchmark file not found: {benchmark_file}")
        return

    if not os.path.exists(sast_file):
        print(f"❌ SAST file not found: {sast_file}")
        return

    print(f"✅ Files found:")
    print(f"   📄 Benchmark: {benchmark_file} ({os.path.getsize(benchmark_file)} bytes)")
    print(f"   📄 SAST: {sast_file} ({os.path.getsize(sast_file)} bytes)")

    # Test JSON validity
    try:
        with open(benchmark_file, 'r') as f:
            benchmark_data = json.load(f)
        print(f"✅ Benchmark JSON is valid ({len(benchmark_data.get('files', []))} files)")
    except Exception as e:
        print(f"❌ Benchmark JSON error: {e}")
        return

    try:
        with open(sast_file, 'r') as f:
            sast_data = json.load(f)
        print(f"✅ SAST JSON is valid ({len(sast_data.get('results', []))} results)")
    except Exception as e:
        print(f"❌ SAST JSON error: {e}")
        return

    # Test web API upload
    print(f"\n🌐 Testing Web API Upload...")
    try:
        with open(benchmark_file, 'rb') as bf, open(sast_file, 'rb') as sf:
            files = {
                'benchmark_file': ('benchmark.json', bf, 'application/json'),
                'sast_file': ('sast.json', sf, 'application/json')
            }
            data = {'format': 'semgrep'}

            response = requests.post('http://127.0.0.1:5000/api/upload', files=files, data=data)

            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Upload successful!")
                print(f"   Session ID: {result.get('session_id')}")
                print(f"   Files: {result.get('files_count')}")
                print(f"   Benchmark vulns: {result.get('total_vulnerabilities', {}).get('benchmark')}")
                print(f"   SAST vulns: {result.get('total_vulnerabilities', {}).get('sast')}")

                # Test session retrieval
                session_id = result.get('session_id')
                session_response = requests.get(f'http://127.0.0.1:5000/api/session/{session_id}')

                if session_response.status_code == 200:
                    session_data = session_response.json()
                    print(f"✅ Session data retrieved: {len(session_data.get('files', []))} files")
                else:
                    print(f"❌ Session retrieval failed: {session_response.status_code}")
                    print(f"   Error: {session_response.text}")

            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_upload()