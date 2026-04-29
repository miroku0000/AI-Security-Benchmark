# tests/test_web_api.py
import pytest
import json
from web_ui.app import create_app

def test_app_creation():
    app = create_app()
    assert app is not None
    assert app.config['TESTING'] is True

def test_health_endpoint():
    app = create_app()
    with app.test_client() as client:
        response = client.get('/api/health')
        assert response.status_code == 200
        assert response.get_json() == {"status": "healthy"}
