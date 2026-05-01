#!/usr/bin/env python3
"""
Automated test for SAST UI workflow
Tests complete user flow: file upload -> accept mappings -> export mappings

Following TDD: This test will fail first, then we implement the infrastructure.
"""

import unittest
import requests
import time
import json
import os
from pathlib import Path

class TestSASTUIWorkflow(unittest.TestCase):
    """Test complete SAST UI workflow from upload to export"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://localhost:5001"
        cls.session = requests.Session()
        cls.test_files_dir = Path("../testsast")

        # Verify server is running
        try:
            response = cls.session.get(f"{cls.base_url}/api/csrf-token")
            response.raise_for_status()
            print(f"✅ Server running at {cls.base_url}")
        except Exception as e:
            raise Exception(f"❌ Server not running: {e}")

    def test_complete_ui_workflow(self):
        """Test complete workflow: upload files -> accept mappings -> export mappings

        This test represents the user story:
        1. User uploads benchmark and SAST files
        2. User accepts first mapping on page 1
        3. User navigates to page 2 and accepts a mapping there
        4. User exports the learned mappings
        """
        # Step 1: Get CSRF token
        csrf_response = self.session.get(f"{self.base_url}/api/csrf-token")
        self.assertEqual(csrf_response.status_code, 200)
        csrf_token = csrf_response.json()["csrf_token"]
        print(f"✅ Got CSRF token: {csrf_token[:20]}...")

        # Step 2: Upload benchmark and SAST files
        session_id = self._upload_test_files(csrf_token)
        print(f"✅ Files uploaded, session: {session_id}")

        # Step 3: Get session data to find mappable items
        session_data = self._get_session_data(session_id)
        print(f"✅ Session data loaded with {len(session_data['files'])} files")

        # Step 4: Accept first mapping on first page
        first_mapping = self._accept_first_mapping(session_id, session_data, csrf_token)
        print(f"✅ Accepted first mapping: {first_mapping}")

        # Step 5: Navigate to second page and accept another mapping
        second_mapping = self._accept_second_page_mapping(session_id, session_data, csrf_token)
        print(f"✅ Accepted second mapping: {second_mapping}")

        # Step 6: Export the learned mappings
        exported_mappings = self._export_mappings(session_id)
        print(f"✅ Exported mappings: {len(exported_mappings.get('mappings', []))} mappings")

        # Verify export contains our accepted mappings
        self.assertGreaterEqual(len(exported_mappings.get('mappings', [])), 2)
        self.assertIn('confirmed_count', exported_mappings)
        self.assertGreaterEqual(exported_mappings['confirmed_count'], 2)

        print("✅ Complete UI workflow test passed!")

    def _upload_test_files(self, csrf_token):
        """Upload benchmark and SAST test files"""
        benchmark_file = self.test_files_dir / "reports.json"
        sast_file = self.test_files_dir / "semgrep-results-allknownbad.json"

        # Verify test files exist
        self.assertTrue(benchmark_file.exists(), f"Benchmark file not found: {benchmark_file}")
        self.assertTrue(sast_file.exists(), f"SAST file not found: {sast_file}")

        # Prepare upload data
        files = {
            'benchmark_file': ('reports.json', open(benchmark_file, 'rb'), 'application/json'),
            'sast_file': ('semgrep-results-allknownbad.json', open(sast_file, 'rb'), 'application/json')
        }
        data = {
            'format': 'semgrep',
            'csrf_token': csrf_token
        }

        # Upload files
        response = self.session.post(f"{self.base_url}/api/upload", files=files, data=data)

        # Clean up file handles
        for file_obj in files.values():
            file_obj[1].close()

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('session_id', result)

        return result['session_id']

    def _get_session_data(self, session_id):
        """Get session data with vulnerability mappings"""
        response = self.session.get(f"{self.base_url}/api/session/{session_id}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def _accept_first_mapping(self, session_id, session_data, csrf_token):
        """Accept first available mapping on first page"""
        # Find first file with both benchmark and SAST vulnerabilities
        for file_data in session_data['files']:
            if (file_data.get('benchmark_vulns') and
                file_data.get('sast_vulns') and
                len(file_data['benchmark_vulns']) > 0 and
                len(file_data['sast_vulns']) > 0):

                benchmark_id = file_data['benchmark_vulns'][0]['id']
                sast_id = file_data['sast_vulns'][0]['id']

                return self._confirm_mapping(session_id, benchmark_id, sast_id, csrf_token)

        self.fail("No mappable vulnerabilities found in session data")

    def _accept_second_page_mapping(self, session_id, session_data, csrf_token):
        """Accept mapping on second page (different file)"""
        # Find second file with mappable vulnerabilities
        mappable_files = [f for f in session_data['files']
                         if f.get('benchmark_vulns') and f.get('sast_vulns') and
                         len(f['benchmark_vulns']) > 0 and len(f['sast_vulns']) > 0]

        self.assertGreaterEqual(len(mappable_files), 2, "Need at least 2 files with mappable vulnerabilities")

        # Use second file
        second_file = mappable_files[1]
        benchmark_id = second_file['benchmark_vulns'][0]['id']
        sast_id = second_file['sast_vulns'][0]['id']

        return self._confirm_mapping(session_id, benchmark_id, sast_id, csrf_token)

    def _confirm_mapping(self, session_id, benchmark_id, sast_id, csrf_token):
        """Confirm a mapping between benchmark and SAST vulnerability"""
        data = {
            'benchmark_id': benchmark_id,
            'sast_id': sast_id,
            'action': 'confirm',
            'csrf_token': csrf_token
        }

        response = self.session.post(
            f"{self.base_url}/api/session/{session_id}/mapping",
            json=data,
            headers={'Content-Type': 'application/json', 'X-CSRF-Token': csrf_token}
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result.get('success'))

        return {'benchmark_id': benchmark_id, 'sast_id': sast_id}

    def _export_mappings(self, session_id):
        """Export learned mappings"""
        response = self.session.get(f"{self.base_url}/api/session/{session_id}/mappings")
        self.assertEqual(response.status_code, 200)
        return response.json()

if __name__ == '__main__':
    # Run the test
    unittest.main(verbosity=2)