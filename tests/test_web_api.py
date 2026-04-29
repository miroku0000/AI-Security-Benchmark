# tests/test_web_api.py
import pytest
import json
import io
from web_ui.app import create_app, cleanup_expired_sessions, sessions

def test_app_creation():
    app = create_app(testing=True)
    assert app is not None
    assert app.config['TESTING'] is True

def test_health_endpoint():
    app = create_app(testing=True)
    with app.test_client() as client:
        response = client.get('/api/health')
        assert response.status_code == 200
        assert response.get_json() == {"status": "healthy"}

def test_session_cleanup():
    """Test that cleanup_expired_sessions removes expired sessions"""
    from datetime import datetime, timedelta
    from web_ui.app import SESSION_TIMEOUT

    # Clear sessions
    sessions.clear()

    # Add an old session
    old_session_id = 'old_session'
    sessions[old_session_id] = {
        'created_at': datetime.now() - SESSION_TIMEOUT - timedelta(hours=1),
        'data': 'test'
    }

    # Add a fresh session
    new_session_id = 'new_session'
    sessions[new_session_id] = {
        'created_at': datetime.now(),
        'data': 'test'
    }

    # Run cleanup
    cleanup_expired_sessions()

    # Verify old session was removed
    assert old_session_id not in sessions
    assert new_session_id in sessions

def test_upload_files():
    app = create_app(testing=True)
    with app.test_client() as client:
        # Mock file uploads
        data = {
            'benchmark_file': (io.BytesIO(b'{"files": []}'), 'benchmark.json'),
            'sast_file': (io.BytesIO(b'{"results": []}'), 'sast.json'),
            'format': 'semgrep'
        }
        response = client.post('/api/upload',
                              data=data,
                              content_type='multipart/form-data')

        assert response.status_code == 200
        json_data = response.get_json()
        assert 'session_id' in json_data
        assert 'files_count' in json_data
        assert 'total_vulnerabilities' in json_data

def test_upload_missing_files():
    app = create_app(testing=True)
    with app.test_client() as client:
        response = client.post('/api/upload', data={})
        assert response.status_code == 400
        assert 'error' in response.get_json()

def test_upload_real_benchmark_schema():
    """Test that real benchmark format with 'files' key is properly parsed"""
    app = create_app(testing=True)
    with app.test_client() as client:
        # Real benchmark format with 'files' key
        benchmark_data = {
            "files": [{
                "test_file": "test.py",
                "vulnerabilities": [{
                    "type": "SQL_INJECTION",
                    "line_number": 10,
                    "severity": "HIGH",
                    "description": "test vuln"
                }]
            }]
        }
        data = {
            'benchmark_file': (io.BytesIO(json.dumps(benchmark_data).encode()), 'benchmark.json'),
            'sast_file': (io.BytesIO(b'{"results": []}'), 'sast.json'),
            'format': 'semgrep'
        }
        response = client.post('/api/upload',
                              data=data,
                              content_type='multipart/form-data')

        assert response.status_code == 200
        json_data = response.get_json()
        assert 'session_id' in json_data
        # This should NOT be 0 with real schema - schema fix is working
        assert json_data['total_vulnerabilities']['benchmark'] == 1
        assert json_data['total_vulnerabilities']['sast'] == 0
