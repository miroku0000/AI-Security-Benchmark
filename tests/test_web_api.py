# tests/test_web_api.py
import pytest
import json
import io
import uuid
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

@pytest.fixture
def test_session_data():
    """Create a test session with sample vulnerabilities"""
    from sast_comparison import Vulnerability

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'created_at': __import__('datetime').datetime.now(),
        'benchmark_vulns': [
            Vulnerability(
                file_path='test.py',
                line_number=10,
                vuln_type='SQL_INJECTION',
                severity='HIGH',
                description='test sql injection',
                source='benchmark'
            ),
            Vulnerability(
                file_path='test2.py',
                line_number=20,
                vuln_type='XSS',
                severity='MEDIUM',
                description='test xss',
                source='benchmark'
            )
        ],
        'sast_vulns': [
            Vulnerability(
                file_path='test.py',
                line_number=10,
                vuln_type='SQL_INJECTION',
                severity='HIGH',
                description='detected sql injection',
                source='sast'
            )
        ],
        'mapping_rules': [],
        'confirmed_mappings': [],
        'denied_mappings': []
    }
    yield {'session_id': session_id}
    # Cleanup
    if session_id in sessions:
        del sessions[session_id]

def test_get_session_data_success(test_session_data):
    """Test successful session data retrieval"""
    app = create_app(testing=True)
    with app.test_client() as client:
        response = client.get(f'/api/session/{test_session_data["session_id"]}')

        assert response.status_code == 200
        data = response.get_json()
        assert "files" in data
        assert "suggestions" in data
        assert "mapping_rules" in data
        assert isinstance(data["files"], list)

def test_get_session_data_not_found():
    """Test session data retrieval with invalid session ID"""
    app = create_app(testing=True)
    with app.test_client() as client:
        response = client.get('/api/session/invalid-session-id')

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Session not found"

def test_get_session_data_empty_session():
    """Test session data retrieval with no vulnerabilities"""
    app = create_app(testing=True)
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'created_at': __import__('datetime').datetime.now(),
        'benchmark_vulns': [],
        'sast_vulns': [],
        'mapping_rules': []
    }

    try:
        with app.test_client() as client:
            response = client.get(f'/api/session/{session_id}')

            assert response.status_code == 200
            data = response.get_json()
            assert data["files"] == []
            assert data["suggestions"] == []
            assert data["mapping_rules"] == []
    finally:
        if session_id in sessions:
            del sessions[session_id]
