#!/usr/bin/env python3
"""
Debug script to test mapping rules upload in isolation
"""

import requests
import json
import tempfile
import os

def test_mapping_rules_upload():
    """Test mapping rules file upload and processing"""
    base_url = "http://localhost:5001"
    session = requests.Session()

    print("🔍 Testing mapping rules upload...")

    # Get CSRF token
    csrf_response = session.get(f"{base_url}/api/csrf-token")
    if csrf_response.status_code != 200:
        print(f"❌ Failed to get CSRF token: {csrf_response.status_code}")
        return

    csrf_token = csrf_response.json()["csrf_token"]
    print(f"✅ Got CSRF token: {csrf_token[:20]}...")

    # Create a simple mapping rules file
    mapping_rules = {
        "mapping_rules": {
            "generic.secrets.security.detected-generic-secret.detected-generic-secret": {
                "benchmark_type": "cryptographic_issue",
                "confidence": 90,
                "source": "debug_test"
            }
        },
        "version": "debug_v1.0"
    }

    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        json.dump(mapping_rules, temp_file, indent=2)
        mapping_rules_file_path = temp_file.name

    print(f"📝 Created mapping rules file: {os.path.basename(mapping_rules_file_path)}")
    print(f"   Content: {json.dumps(mapping_rules, indent=2)}")

    try:
        # Upload files with mapping rules
        benchmark_file_path = "../testsast/reports.json"
        sast_file_path = "../testsast/semgrep-results-allknownbad.json"

        files = {
            'benchmark_file': ('reports.json', open(benchmark_file_path, 'rb'), 'application/json'),
            'sast_file': ('semgrep-results-allknownbad.json', open(sast_file_path, 'rb'), 'application/json'),
            'mapping_rules_file': ('mapping_rules.json', open(mapping_rules_file_path, 'rb'), 'application/json')
        }
        data = {
            'format': 'semgrep',
            'csrf_token': csrf_token
        }

        print("📤 Uploading files with mapping rules...")
        response = session.post(f"{base_url}/api/upload", files=files, data=data)

        # Clean up file handles
        for file_obj in files.values():
            file_obj[1].close()

        print(f"📊 Upload response: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            session_id = result['session_id']
            print(f"✅ Upload successful, session: {session_id}")

            # Check if mappings were auto-applied
            mappings_response = session.get(f"{base_url}/api/session/{session_id}/mappings")
            if mappings_response.status_code == 200:
                mappings_data = mappings_response.json()
                confirmed_count = mappings_data.get('confirmed_count', 0)
                print(f"📈 Auto-applied mappings: {confirmed_count}")

                if confirmed_count > 0:
                    print("✅ Mapping rules were successfully auto-applied!")
                else:
                    print("❌ No mappings were auto-applied from rules file")

                    # Debug: Check session details
                    session_response = session.get(f"{base_url}/api/session/{session_id}")
                    if session_response.status_code == 200:
                        session_data = session_response.json()
                        total_files = len(session_data.get('files', []))
                        print(f"🔍 Session has {total_files} files loaded")
            else:
                print(f"❌ Failed to get mappings: {mappings_response.status_code}")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Error text: {response.text}")

    finally:
        # Clean up temporary file
        os.unlink(mapping_rules_file_path)

if __name__ == '__main__':
    test_mapping_rules_upload()