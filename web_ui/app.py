# web_ui/app.py
from flask import Flask, jsonify, request, send_from_directory
import uuid
import os
from datetime import datetime, timedelta

# Import existing SAST comparison logic
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sast_comparison import SASTComparison

# Global session storage (in-memory for simplicity)
sessions = {}
SESSION_TIMEOUT = timedelta(hours=4)

def create_app(testing=False):
    app = Flask(__name__, static_folder='static')
    app.config['TESTING'] = testing

    @app.route('/api/health')
    def health():
        return jsonify({"status": "healthy"})

    @app.route('/')
    def index():
        return send_from_directory('static', 'index.html')

    @app.before_request
    def cleanup_sessions():
        cleanup_expired_sessions()

    return app

def cleanup_expired_sessions():
    """Remove sessions older than SESSION_TIMEOUT"""
    current_time = datetime.now()
    expired_sessions = []

    for session_id, session_data in sessions.items():
        if current_time - session_data['created_at'] > SESSION_TIMEOUT:
            expired_sessions.append(session_id)

    for session_id in expired_sessions:
        del sessions[session_id]

if __name__ == '__main__':
    app = create_app()
    debug = os.environ.get('FLASK_DEBUG') == '1'
    app.run(debug=debug, port=5000)
