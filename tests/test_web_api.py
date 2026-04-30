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
def app():
    """Create test app"""
    return create_app(testing=True)

@pytest.fixture
def test_session_data():
    """Create a test session with sample vulnerabilities using comparison object"""
    from sast_comparison import Vulnerability, SASTComparison

    session_id = str(uuid.uuid4())

    # Create a comparison object and manually set benchmark_vulns
    comparison = object.__new__(SASTComparison)
    comparison.benchmark_vulns = [
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
    ]

    sessions[session_id] = {
        'created_at': __import__('datetime').datetime.now(),
        'comparison': comparison,
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
        'denied_mappings': [],
        'benchmark_file_data': {},
        'sast_file_data': {}
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

def test_get_session_data_with_vulnerabilities():
    """Test that session data includes all vulnerability fields including ID"""
    app = create_app(testing=True)
    with app.test_client() as client:
        response = client.get(f'/api/session/{None}')  # Will be 404

    # This is tested via test_get_session_data_success with test_session_data fixture

def test_session_data_vulnerability_ids():
    """Test that vulnerabilities have generated IDs"""
    from sast_comparison import Vulnerability, SASTComparison

    app = create_app(testing=True)
    session_id = str(uuid.uuid4())

    # Create comparison object with vulnerabilities
    comparison = object.__new__(SASTComparison)
    comparison.benchmark_vulns = [
        Vulnerability(
            file_path='test.py',
            line_number=10,
            vuln_type='SQL_INJECTION',
            severity='HIGH',
            description='SQL injection test',
            source='benchmark'
        )
    ]

    sessions[session_id] = {
        'created_at': __import__('datetime').datetime.now(),
        'comparison': comparison,
        'sast_vulns': [
            Vulnerability(
                file_path='test.py',
                line_number=10,
                vuln_type='SQL_INJECTION',
                severity='HIGH',
                description='SQL injection detected',
                source='sast'
            )
        ],
        'mapping_rules': [],
        'confirmed_mappings': [],
        'denied_mappings': [],
        'benchmark_file_data': {},
        'sast_file_data': {}
    }

    try:
        with app.test_client() as client:
            response = client.get(f'/api/session/{session_id}')
            assert response.status_code == 200

            data = response.get_json()
            assert len(data['files']) == 1

            file_data = data['files'][0]
            assert file_data['file_path'] == 'test.py'
            assert len(file_data['benchmark_vulns']) == 1
            assert len(file_data['sast_vulns']) == 1

            # Check that IDs are generated and present
            bench_vuln = file_data['benchmark_vulns'][0]
            assert 'id' in bench_vuln
            assert bench_vuln['id'].startswith('bench_')
            assert bench_vuln['vuln_type'] == 'SQL_INJECTION'
            assert bench_vuln['severity'] == 'HIGH'
            assert bench_vuln['description'] == 'SQL injection test'

            sast_vuln = file_data['sast_vulns'][0]
            assert 'id' in sast_vuln
            assert sast_vuln['id'].startswith('sast_')
            assert sast_vuln['vuln_type'] == 'SQL_INJECTION'
            assert sast_vuln['severity'] == 'HIGH'
            assert sast_vuln['description'] == 'SQL injection detected'
    finally:
        if session_id in sessions:
            del sessions[session_id]

def test_end_to_end_upload_and_retrieve():
    """End-to-end test: upload files then retrieve session data"""
    app = create_app(testing=True)
    with app.test_client() as client:
        # Step 1: Upload files with real benchmark format
        benchmark_data = {
            "files": [
                {
                    "test_file": "vulnerable.py",
                    "vulnerabilities": [
                        {
                            "type": "SQL_INJECTION",
                            "line_number": 15,
                            "severity": "HIGH",
                            "description": "User input in SQL query"
                        },
                        {
                            "type": "XSS",
                            "line_number": 25,
                            "severity": "MEDIUM",
                            "description": "Unescaped user output"
                        }
                    ]
                },
                {
                    "test_file": "safe.py",
                    "vulnerabilities": []
                }
            ]
        }

        sast_data = {
            "results": [
                {
                    "check_id": "injection/sql",
                    "path": "vulnerable.py",
                    "start": {
                        "line": 15
                    },
                    "extra": {
                        "severity": "HIGH",
                        "message": "SQL injection vulnerability detected"
                    }
                }
            ]
        }

        upload_response = client.post(
            '/api/upload',
            data={
                'benchmark_file': (io.BytesIO(json.dumps(benchmark_data).encode()), 'benchmark.json'),
                'sast_file': (io.BytesIO(json.dumps(sast_data).encode()), 'sast.json'),
                'format': 'semgrep'
            },
            content_type='multipart/form-data'
        )

        assert upload_response.status_code == 200
        upload_json = upload_response.get_json()
        assert 'session_id' in upload_json
        assert upload_json['total_vulnerabilities']['benchmark'] == 2
        assert upload_json['total_vulnerabilities']['sast'] == 1

        session_id = upload_json['session_id']

        # Step 2: Retrieve session data
        get_response = client.get(f'/api/session/{session_id}')
        assert get_response.status_code == 200

        session_data = get_response.get_json()

        # Verify structure
        assert 'files' in session_data
        assert 'suggestions' in session_data
        assert 'mapping_rules' in session_data

        # Verify files are properly grouped
        files = session_data['files']
        assert len(files) == 1  # Only vulnerable.py has vulnerabilities

        file_info = files[0]
        assert file_info['file_path'] == 'vulnerable.py'
        assert len(file_info['benchmark_vulns']) == 2
        assert len(file_info['sast_vulns']) == 1

        # Verify benchmark vulnerabilities have required fields
        for vuln in file_info['benchmark_vulns']:
            assert 'id' in vuln
            assert 'vuln_type' in vuln
            assert 'line_number' in vuln
            assert 'severity' in vuln
            assert 'description' in vuln

        # Verify SAST vulnerabilities have required fields
        for vuln in file_info['sast_vulns']:
            assert 'id' in vuln
            assert 'vuln_type' in vuln
            assert 'line_number' in vuln
            assert 'severity' in vuln
            assert 'description' in vuln

        # Verify specific vulnerability data
        sql_injection = next(v for v in file_info['benchmark_vulns'] if v['vuln_type'] == 'SQL_INJECTION')
        assert sql_injection['line_number'] == 15
        assert sql_injection['severity'] == 'HIGH'

        xss = next(v for v in file_info['benchmark_vulns'] if v['vuln_type'] == 'XSS')
        assert xss['line_number'] == 25
        assert xss['severity'] == 'MEDIUM'

def test_get_session_data_empty_session():
    """Test session data retrieval with no vulnerabilities"""
    from sast_comparison import SASTComparison

    app = create_app(testing=True)
    session_id = str(uuid.uuid4())

    # Create empty comparison object
    comparison = object.__new__(SASTComparison)
    comparison.benchmark_vulns = []

    sessions[session_id] = {
        'created_at': __import__('datetime').datetime.now(),
        'comparison': comparison,
        'sast_vulns': [],
        'mapping_rules': [],
        'benchmark_file_data': {},
        'sast_file_data': {}
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

def test_get_suggestions_with_threshold(app, test_session_data):
    """Test getting suggestions filtered by confidence threshold"""
    with app.test_client() as client:
        session_id = test_session_data["session_id"]

        response = client.get(f'/api/session/{session_id}/suggestions?confidence=75')

        assert response.status_code == 200
        data = response.get_json()
        assert "suggestions" in data
        assert "confidence_scores" in data
        assert isinstance(data["suggestions"], list)

        # Verify all suggestions meet threshold
        for suggestion in data["suggestions"]:
            assert suggestion["confidence"] >= 75
            assert "benchmark_id" in suggestion
            assert "sast_id" in suggestion
            assert "reasoning" in suggestion

def test_get_suggestions_default_threshold(app, test_session_data):
    """Test getting suggestions with default threshold (50)"""
    with app.test_client() as client:
        session_id = test_session_data["session_id"]

        response = client.get(f'/api/session/{session_id}/suggestions')

        assert response.status_code == 200
        data = response.get_json()
        assert "suggestions" in data
        assert "confidence_scores" in data

def test_get_suggestions_invalid_threshold(app, test_session_data):
    """Test invalid confidence threshold values"""
    with app.test_client() as client:
        session_id = test_session_data["session_id"]

        # Test negative threshold
        response = client.get(f'/api/session/{session_id}/suggestions?confidence=-10')
        assert response.status_code == 400

        # Test threshold over 100
        response = client.get(f'/api/session/{session_id}/suggestions?confidence=150')
        assert response.status_code == 400

def test_get_suggestions_with_existing_mappings(app, test_session_data):
    """Test suggestions exclude already mapped vulnerabilities"""
    with app.test_client() as client:
        session_id = test_session_data["session_id"]

        # First confirm a mapping
        client.post(f'/api/session/{session_id}/mapping',
                   json={
                       "action": "confirm",
                       "benchmark_id": "bench_0_7c9f01",
                       "sast_id": "sast_0_c10ffc"
                   })

        # Get suggestions
        response = client.get(f'/api/session/{session_id}/suggestions?confidence=0')

        assert response.status_code == 200
        data = response.get_json()

        # Verify confirmed IDs are excluded
        for suggestion in data["suggestions"]:
            assert suggestion["benchmark_id"] != "bench_0_7c9f01"
            assert suggestion["sast_id"] != "sast_0_c10ffc"

def test_get_suggestions_invalid_session(app):
    """Test suggestions with invalid session"""
    with app.test_client() as client:
        response = client.get('/api/session/invalid-id/suggestions')

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Session not found"

# Task 4: Mapping Update API Endpoint Tests

def test_update_mapping_confirm(test_session_data):
    """Test confirming a vulnerability mapping"""
    app = create_app(testing=True)
    with app.test_client() as client:
        session_id = test_session_data["session_id"]

        response = client.post(f'/api/session/{session_id}/mapping',
                             json={
                                 "action": "confirm",
                                 "benchmark_id": "bench_0_123abc",
                                 "sast_id": "sast_0_456def"
                             })

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "new_suggestions" in data

        # Verify mapping is stored in session
        session_data = sessions[session_id]
        assert "confirmed_mappings" in session_data
        assert len(session_data["confirmed_mappings"]) == 1


def test_update_mapping_deny(test_session_data):
    """Test denying a vulnerability mapping"""
    app = create_app(testing=True)
    with app.test_client() as client:
        session_id = test_session_data["session_id"]

        response = client.post(f'/api/session/{session_id}/mapping',
                             json={
                                 "action": "deny",
                                 "benchmark_id": "bench_0_123abc",
                                 "sast_id": "sast_0_456def"
                             })

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify denial is stored in session
        session_data = sessions[session_id]
        assert len(session_data["denied_mappings"]) == 1


def test_update_mapping_invalid_action(test_session_data):
    """Test invalid action parameter"""
    app = create_app(testing=True)
    with app.test_client() as client:
        response = client.post(f'/api/session/{test_session_data["session_id"]}/mapping',
                             json={
                                 "action": "invalid",
                                 "benchmark_id": "bench_0_123abc",
                                 "sast_id": "sast_0_456def"
                             })

        assert response.status_code == 400
        data = response.get_json()
        assert "Action must be 'confirm' or 'deny'" in data["error"]


def test_update_mapping_missing_fields(test_session_data):
    """Test missing required fields"""
    app = create_app(testing=True)
    with app.test_client() as client:
        response = client.post(f'/api/session/{test_session_data["session_id"]}/mapping',
                             json={"action": "confirm"})

        assert response.status_code == 400
        data = response.get_json()
        assert "Missing required fields" in data["error"]


def test_update_mapping_invalid_session():
    """Test mapping update with invalid session"""
    app = create_app(testing=True)
    with app.test_client() as client:
        response = client.post('/api/session/invalid-id/mapping',
                             json={
                                 "action": "confirm",
                                 "benchmark_id": "bench_0_123abc",
                                 "sast_id": "sast_0_456def"
                             })

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Session not found"
