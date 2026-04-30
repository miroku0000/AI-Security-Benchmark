# web_ui/app.py
from flask import Flask, jsonify, request, send_from_directory
import uuid
import os
from datetime import datetime, timedelta
import io
import json

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
    app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB limit
    app.sessions = sessions  # Store sessions reference on app

    @app.route('/api/health')
    def health():
        return jsonify({"status": "healthy"})

    @app.route('/api/upload', methods=['POST'])
    def upload_files():
        cleanup_expired_sessions()

        # Validate required files
        if 'benchmark_file' not in request.files or 'sast_file' not in request.files:
            return jsonify({"error": "Missing benchmark_file or sast_file"}), 400

        if 'format' not in request.form:
            return jsonify({"error": "Missing format parameter"}), 400

        benchmark_file = request.files['benchmark_file']
        sast_file = request.files['sast_file']
        format_type = request.form['format']

        try:
            # Create new session
            session_id = str(uuid.uuid4())

            # Save uploaded files temporarily
            try:
                benchmark_content = json.loads(benchmark_file.read().decode('utf-8'))
                sast_content = json.loads(sast_file.read().decode('utf-8'))
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON format in uploaded files"}), 400

            # Initialize SAST comparison with uploaded data
            # Create a temporary instance without using the file-based constructor
            comparison = object.__new__(SASTComparison)
            comparison._load_benchmark_data_from_dict(benchmark_content)

            # Parse SAST results based on format
            sast_vulns = []
            if format_type == 'semgrep':
                sast_vulns = comparison._parse_sast_results_from_dict(sast_content, format_type)

            # Store session data
            sessions[session_id] = {
                'created_at': datetime.now(),
                'comparison': comparison,
                'sast_vulns': sast_vulns,
                'confirmed_mappings': [],
                'denied_mappings': [],
                'mapping_rules': [],
                'benchmark_file_data': benchmark_content,
                'sast_file_data': sast_content
            }

            return jsonify({
                "session_id": session_id,
                "files_count": len(comparison.benchmark_vulns),
                "total_vulnerabilities": {
                    "benchmark": len(comparison.benchmark_vulns),
                    "sast": len(sast_vulns)
                }
            })

        except Exception as e:
            # Log the real error server-side but don't leak it
            app.logger.error(f"File processing error: {str(e)}")
            return jsonify({"error": "Failed to process uploaded files"}), 500

    @app.route('/api/session/<session_id>', methods=['GET'])
    def get_session_data(session_id):
        """Get session vulnerability data grouped by files"""
        if session_id not in app.sessions:
            return jsonify({"error": "Session not found"}), 404

        session_data = app.sessions[session_id]

        # Group vulnerabilities by file path
        files_grouped = {}
        for vuln in session_data['benchmark_vulns']:
            file_path = vuln.file_path
            if file_path not in files_grouped:
                files_grouped[file_path] = {
                    "file_path": file_path,
                    "benchmark_vulns": [],
                    "sast_vulns": []
                }
            files_grouped[file_path]["benchmark_vulns"].append({
                "id": vuln.id if hasattr(vuln, 'id') else None,
                "vuln_type": vuln.vuln_type,
                "line_number": vuln.line_number
            })

        for vuln in session_data['sast_vulns']:
            file_path = vuln.file_path
            if file_path not in files_grouped:
                files_grouped[file_path] = {
                    "file_path": file_path,
                    "benchmark_vulns": [],
                    "sast_vulns": []
                }
            files_grouped[file_path]["sast_vulns"].append({
                "id": vuln.id if hasattr(vuln, 'id') else None,
                "vuln_type": vuln.vuln_type,
                "line_number": vuln.line_number
            })

        return jsonify({
            "files": list(files_grouped.values()),
            "suggestions": [],  # Empty for now, will be implemented in Task 5
            "mapping_rules": session_data.get('mapping_rules', [])
        })

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
