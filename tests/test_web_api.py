# tests/test_web_api.py
import pytest
import json
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
