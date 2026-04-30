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
from sast_comparison import SASTComparison, Vulnerability

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

        # Access benchmark_vulns from the comparison object
        comparison = session_data['comparison']
        for idx, vuln in enumerate(comparison.benchmark_vulns):
            file_path = vuln.file_path
            if file_path not in files_grouped:
                files_grouped[file_path] = {
                    "file_path": file_path,
                    "benchmark_vulns": [],
                    "sast_vulns": []
                }
            files_grouped[file_path]["benchmark_vulns"].append({
                "id": f"bench_{idx}_{hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF:06x}",
                "vuln_type": vuln.vuln_type,
                "line_number": vuln.line_number,
                "severity": vuln.severity,
                "description": vuln.description
            })

        for idx, vuln in enumerate(session_data['sast_vulns']):
            file_path = vuln.file_path
            if file_path not in files_grouped:
                files_grouped[file_path] = {
                    "file_path": file_path,
                    "benchmark_vulns": [],
                    "sast_vulns": []
                }
            files_grouped[file_path]["sast_vulns"].append({
                "id": f"sast_{idx}_{hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF:06x}",
                "vuln_type": vuln.vuln_type,
                "line_number": vuln.line_number,
                "severity": vuln.severity,
                "description": vuln.description
            })

        # Filter out files with no vulnerabilities
        files_list = [f for f in files_grouped.values()
                     if f["benchmark_vulns"] or f["sast_vulns"]]

        return jsonify({
            "files": files_list,
            "suggestions": [],  # Empty for now, will be implemented in Task 5
            "mapping_rules": session_data.get('mapping_rules', [])
        })

    @app.route('/api/session/<session_id>/mapping', methods=['POST'])
    def update_mapping(session_id):
        """Update confirmed/denied mappings and create pattern rules"""
        if session_id not in app.sessions:
            return jsonify({"error": "Session not found"}), 404

        if not request.json:
            return jsonify({"error": "JSON data required"}), 400

        data = request.json
        action = data.get('action')
        benchmark_id = data.get('benchmark_id')
        sast_id = data.get('sast_id')

        if not all([action, benchmark_id, sast_id]):
            return jsonify({"error": "Missing required fields: action, benchmark_id, sast_id"}), 400

        if action not in ['confirm', 'deny']:
            return jsonify({"error": "Action must be 'confirm' or 'deny'"}), 400

        session_data = app.sessions[session_id]

        # Initialize mapping storage if not exists
        if 'confirmed_mappings' not in session_data:
            session_data['confirmed_mappings'] = []
        if 'denied_mappings' not in session_data:
            session_data['denied_mappings'] = []
        if 'mapping_rules' not in session_data:
            session_data['mapping_rules'] = []

        mapping = {
            "benchmark_id": benchmark_id,
            "sast_id": sast_id,
            "manual": True
        }

        if action == 'confirm':
            session_data['confirmed_mappings'].append(mapping)

            # Create pattern rule for learning
            rule = create_pattern_rule(session_data, benchmark_id, sast_id)
            if rule:
                session_data['mapping_rules'].append(rule)

        elif action == 'deny':
            session_data['denied_mappings'].append(mapping)

        # Generate new suggestions based on updated rules (placeholder for now)
        new_suggestions = []

        return jsonify({
            "success": True,
            "new_suggestions": new_suggestions
        })

    @app.route('/api/session/<session_id>/suggestions', methods=['GET'])
    def get_suggestions(session_id):
        """Get auto-suggestions filtered by confidence threshold"""
        if session_id not in app.sessions:
            return jsonify({"error": "Session not found"}), 404

        # Get confidence threshold from query params (default 50)
        confidence_threshold = request.args.get('confidence', 50, type=int)

        if confidence_threshold < 0 or confidence_threshold > 100:
            return jsonify({"error": "Confidence threshold must be between 0 and 100"}), 400

        session_data = app.sessions[session_id]

        # Use SastComparison to generate suggestions
        comparison = session_data['comparison']
        suggestions = comparison.generate_suggestions(session_data, confidence_threshold)

        # Build confidence scores summary
        confidence_scores = {}
        for suggestion in suggestions:
            score_range = f"{(suggestion['confidence'] // 10) * 10}-{(suggestion['confidence'] // 10) * 10 + 9}"
            confidence_scores[score_range] = confidence_scores.get(score_range, 0) + 1

        return jsonify({
            "suggestions": suggestions,
            "confidence_scores": confidence_scores
        })

    @app.route('/api/session/<session_id>/export', methods=['GET'])
    def export_mapping(session_id):
        """Generate final mapping JSON for CLI tool compatibility"""
        if session_id not in app.sessions:
            return jsonify({"error": "Session not found"}), 404

        session_data = app.sessions[session_id]
        comparison = session_data['comparison']

        # Build export data structure compatible with CLI tool
        export_data = {
            "confirmed_mappings": [],
            "denied_mappings": [],
            "mapping_statistics": {
                "total_benchmark_vulns": len(comparison.benchmark_vulns),
                "total_sast_vulns": len(session_data['sast_vulns']),
                "confirmed_mappings": len(session_data.get('confirmed_mappings', [])),
                "denied_mappings": len(session_data.get('denied_mappings', [])),
                "mapping_coverage": 0.0
            },
            "pattern_rules": session_data.get('mapping_rules', []),
            "export_metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "generated_by": "web_ui"
            }
        }

        # Convert confirmed mappings to CLI format
        for mapping in session_data.get('confirmed_mappings', []):
            benchmark_vuln = find_vulnerability_by_id(mapping['benchmark_id'], comparison.benchmark_vulns, 'bench')
            sast_vuln = find_vulnerability_by_id(mapping['sast_id'], session_data['sast_vulns'], 'sast')

            if benchmark_vuln and sast_vuln:
                export_data["confirmed_mappings"].append({
                    "benchmark": {
                        "file_path": benchmark_vuln.file_path,
                        "line_number": benchmark_vuln.line_number,
                        "vuln_type": benchmark_vuln.vuln_type,
                        "severity": getattr(benchmark_vuln, 'severity', 'UNKNOWN'),
                        "description": getattr(benchmark_vuln, 'description', '')
                    },
                    "sast": {
                        "file_path": sast_vuln.file_path,
                        "line_number": sast_vuln.line_number,
                        "vuln_type": sast_vuln.vuln_type,
                        "severity": getattr(sast_vuln, 'severity', 'UNKNOWN'),
                        "description": getattr(sast_vuln, 'description', '')
                    },
                    "confidence_score": calculate_mapping_confidence(benchmark_vuln, sast_vuln, session_data.get('mapping_rules', []))
                })

        # Convert denied mappings to CLI format
        for mapping in session_data.get('denied_mappings', []):
            benchmark_vuln = find_vulnerability_by_id(mapping['benchmark_id'], comparison.benchmark_vulns, 'bench')
            sast_vuln = find_vulnerability_by_id(mapping['sast_id'], session_data['sast_vulns'], 'sast')

            if benchmark_vuln and sast_vuln:
                export_data["denied_mappings"].append({
                    "benchmark": {
                        "file_path": benchmark_vuln.file_path,
                        "line_number": benchmark_vuln.line_number,
                        "vuln_type": benchmark_vuln.vuln_type
                    },
                    "sast": {
                        "file_path": sast_vuln.file_path,
                        "line_number": sast_vuln.line_number,
                        "vuln_type": sast_vuln.vuln_type
                    }
                })

        # Calculate mapping coverage
        total_benchmark = export_data["mapping_statistics"]["total_benchmark_vulns"]
        if total_benchmark > 0:
            export_data["mapping_statistics"]["mapping_coverage"] = round(
                (export_data["mapping_statistics"]["confirmed_mappings"] / total_benchmark) * 100, 2
            )

        # Create downloadable response
        response = jsonify(export_data)
        response.headers['Content-Disposition'] = f'attachment; filename=vulnerability_mapping_{session_id[:8]}.json'
        response.headers['Content-Type'] = 'application/json'

        return response

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


def create_pattern_rule(session_data, benchmark_id, sast_id):
    """Create a pattern rule from confirmed mapping"""
    # Find the actual vulnerability objects
    comparison = session_data['comparison']

    benchmark_vuln = None
    for idx, vuln in enumerate(comparison.benchmark_vulns):
        generated_id = f"bench_{idx}_{hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF:06x}"
        if generated_id == benchmark_id:
            benchmark_vuln = vuln
            break

    sast_vuln = None
    for idx, vuln in enumerate(session_data['sast_vulns']):
        generated_id = f"sast_{idx}_{hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF:06x}"
        if generated_id == sast_id:
            sast_vuln = vuln
            break

    if not benchmark_vuln or not sast_vuln:
        return None

    return {
        "benchmark_type": benchmark_vuln.vuln_type,
        "sast_pattern": sast_vuln.vuln_type,
        "file_extension_match": benchmark_vuln.file_path.endswith(sast_vuln.file_path.split('.')[-1]),
        "confidence_boost": 0.4,
        "line_proximity_weight": abs(benchmark_vuln.line_number - sast_vuln.line_number)
    }


def find_vulnerability_by_id(vuln_id, vulnerability_list, vuln_type_prefix):
    """Find vulnerability object by generated ID"""
    for idx, vuln in enumerate(vulnerability_list):
        generated_id = f"{vuln_type_prefix}_{idx}_{hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF:06x}"
        if generated_id == vuln_id:
            return vuln
    return None


def calculate_mapping_confidence(benchmark_vuln, sast_vuln, mapping_rules):
    """Calculate confidence score for a confirmed mapping"""
    # Use the same logic as enhanced_confidence_score but create dummy comparison
    try:
        temp_comparison = SASTComparison.__new__(SASTComparison)
        return temp_comparison.enhanced_confidence_score(benchmark_vuln, sast_vuln, mapping_rules)
    except Exception:
        # Fallback to simple confidence calculation
        base_score = 0.5  # Basic similarity
        if benchmark_vuln.file_path == sast_vuln.file_path:
            base_score += 0.3
        if benchmark_vuln.vuln_type.lower() in sast_vuln.vuln_type.lower():
            base_score += 0.2
        return min(100, base_score * 100)

if __name__ == '__main__':
    app = create_app()
    debug = os.environ.get('FLASK_DEBUG') == '1'
    app.run(debug=debug, port=5000)
