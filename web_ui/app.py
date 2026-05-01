# -*- coding: utf-8 -*-
# web_ui/app.py
from flask import Flask, jsonify, request, send_from_directory, render_template, session
from flask_cors import CORS
import uuid
import os
from datetime import datetime, timedelta
import io
import json
import re
from werkzeug.utils import secure_filename
from collections import defaultdict, deque
import time
import binascii

# Import existing SAST comparison logic
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'testsast'))
from testsast.sast_comparison import SASTComparison, Vulnerability
from security import SecurityValidator

# Global session storage (in-memory for simplicity)
sessions = {}
SESSION_TIMEOUT = timedelta(hours=4)

# Rate limiting storage
rate_limits = defaultdict(lambda: deque())
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_MINUTE = 30

def create_app(testing=False):
    app = Flask(__name__,
               template_folder='templates',
               static_folder='static')
    app.config['TESTING'] = testing
    app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB limit
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', binascii.hexlify(os.urandom(32)).decode('ascii'))
    app.sessions = sessions  # Store sessions reference on app

    # Configure CORS for API endpoints (if needed for cross-origin requests)
    # For localhost development, this is usually not needed
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5000", "http://localhost:5001", "http://127.0.0.1:5000", "http://127.0.0.1:5001"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token"]
        }
    })

    # Security headers
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # Generate nonce for inline scripts
        nonce = binascii.hexlify(os.urandom(16)).decode('ascii')
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'nonce-" + nonce + "'; "
            "style-src 'self' 'unsafe-inline'; "  # Keep for CSS simplicity
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests"
        )
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = (
            "accelerometer=(), ambient-light-sensor=(), autoplay=(), "
            "battery=(), camera=(), cross-origin-isolated=(), display-capture=(), "
            "document-domain=(), encrypted-media=(), execution-while-not-rendered=(), "
            "execution-while-out-of-viewport=(), fullscreen=(), geolocation=(), "
            "gyroscope=(), keyboard-map=(), magnetometer=(), microphone=(), "
            "midi=(), navigation-override=(), payment=(), picture-in-picture=(), "
            "publickey-credentials-get=(), screen-wake-lock=(), sync-xhr=(), "
            "usb=(), web-share=(), xr-spatial-tracking=()"
        )
        return response

    @app.route('/api/health')
    def health():
        return jsonify({"status": "healthy"})

    @app.route('/api/csrf-token')
    def get_csrf_token():
        """Generate and return a CSRF token"""
        if 'csrf_token' not in session:
            session['csrf_token'] = binascii.hexlify(os.urandom(32)).decode('ascii')
        return jsonify({"csrf_token": session['csrf_token']})

    @app.route('/api/upload', methods=['POST'])
    def upload_files():
        cleanup_expired_sessions()

        # Security: CSRF Protection
        csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            return jsonify({"error": "Invalid CSRF token"}), 403

        # Validate required files
        if 'benchmark_file' not in request.files or 'sast_file' not in request.files:
            return jsonify({"error": "Missing benchmark_file or sast_file"}), 400

        if 'format' not in request.form:
            return jsonify({"error": "Missing format parameter"}), 400

        benchmark_file = request.files['benchmark_file']
        sast_file = request.files['sast_file']
        mapping_rules_file = request.files.get('mapping_rules_file')  # Optional
        format_type = request.form['format']

        # Debug: Log what files were uploaded
        app.logger.info(f"Upload request: benchmark={benchmark_file.filename}, sast={sast_file.filename}, mapping_rules={'YES' if mapping_rules_file else 'NO'}")
        if mapping_rules_file:
            app.logger.info(f"Mapping rules file: {mapping_rules_file.filename}, size: {mapping_rules_file.content_length or 'unknown'}")

        # Security: Validate filenames
        try:
            benchmark_filename = SecurityValidator.validate_filename(benchmark_file.filename)
            sast_filename = SecurityValidator.validate_filename(sast_file.filename)
            if mapping_rules_file:
                mapping_rules_filename = SecurityValidator.validate_filename(mapping_rules_file.filename)
        except ValueError as e:
            return jsonify({"error": "Invalid filename: " + str(e)}), 400

        # Security: Validate format parameter
        if format_type not in ['semgrep', 'json']:
            return jsonify({"error": "Invalid format parameter"}), 400

        try:
            # Security: Create new secure session with rotation
            session_id = str(uuid.uuid4())

            # Generate new CSRF token for this session
            if 'csrf_token' not in session:
                session['csrf_token'] = binascii.hexlify(os.urandom(32)).decode('ascii')

            # Security: Safely parse uploaded JSON files
            try:
                benchmark_raw = benchmark_file.read()
                sast_raw = sast_file.read()

                # Validate file sizes
                if len(benchmark_raw) > app.config['MAX_CONTENT_LENGTH']:
                    return jsonify({"error": "Benchmark file too large"}), 400
                if len(sast_raw) > app.config['MAX_CONTENT_LENGTH']:
                    return jsonify({"error": "SAST file too large"}), 400

                # Securely parse JSON content
                benchmark_content = SecurityValidator.validate_json_content(benchmark_raw)
                sast_content = SecurityValidator.validate_json_content(sast_raw)

                # Parse mapping rules if provided
                mapping_rules_content = None
                if mapping_rules_file:
                    mapping_rules_raw = mapping_rules_file.read()
                    if len(mapping_rules_raw) > 10 * 1024 * 1024:  # 10MB limit for mapping rules
                        return jsonify({"error": "Mapping rules file too large"}), 400
                    mapping_rules_content = SecurityValidator.validate_json_content(mapping_rules_raw)

            except ValueError as e:
                return jsonify({"error": "File validation failed: " + str(e)}), 400
            except Exception as e:
                app.logger.error("File parsing error: " + str(e))
                return jsonify({"error": "Failed to process uploaded files"}), 400

            # Initialize SAST comparison with uploaded data
            # Create a temporary instance without using the file-based constructor
            comparison = object.__new__(SASTComparison)
            comparison.benchmark_vulns = []
            comparison.sast_vulns = []  # Initialize this too

            # Handle simple list format
            if isinstance(benchmark_content, list):
                for vuln_data in benchmark_content:
                    comparison.benchmark_vulns.append(Vulnerability(
                        file_path=vuln_data.get('file_path', ''),
                        line_number=vuln_data.get('line_number', 0),
                        vuln_type=vuln_data.get('vuln_type', 'UNKNOWN'),
                        severity=vuln_data.get('severity', 'MEDIUM'),
                        description=vuln_data.get('description', ''),
                        source='benchmark'
                    ))
            else:
                # Use original method for complex format
                comparison._load_benchmark_data_from_dict(benchmark_content)

            # Parse SAST results based on format
            sast_vulns = []
            if format_type == 'semgrep':
                parsed_vulns = comparison._parse_sast_results_from_dict(sast_content, format_type)
                # Add IDs to parsed vulnerabilities
                for idx, vuln in enumerate(parsed_vulns):
                    # Add the same ID that will be used in API responses
                    vuln.id = "sast_{}_{:06x}".format(idx, hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF)
                    sast_vulns.append(vuln)

            # Store session data
            session_data = {
                'created_at': datetime.now(),
                'comparison': comparison,
                'sast_vulns': sast_vulns,
                'confirmed_mappings': [],
                'denied_mappings': [],
                'mapping_rules': [],
                'benchmark_file_data': benchmark_content,
                'sast_file_data': sast_content
            }

            # Process mapping rules if provided
            if mapping_rules_content:
                try:
                    app.logger.info(f"Processing mapping rules content: {type(mapping_rules_content)}")
                    app.logger.info(f"Mapping rules keys: {list(mapping_rules_content.keys()) if isinstance(mapping_rules_content, dict) else 'not a dict'}")

                    # Validate mapping rules structure
                    if 'mapping_rules' in mapping_rules_content:
                        # Limit number of mapping rules (dict items, not slice)
                        all_rules = mapping_rules_content['mapping_rules']
                        app.logger.info(f"Found mapping_rules with {len(all_rules) if isinstance(all_rules, dict) else 'non-dict'} entries")
                        if isinstance(all_rules, dict):
                            limited_rules = dict(list(all_rules.items())[:1000])  # Limit to 1000 rules
                            session_data['mapping_rules'] = limited_rules
                        else:
                            session_data['mapping_rules'] = all_rules
                        app.logger.info("Loaded {} mapping rules from upload".format(len(session_data['mapping_rules'])))
                    else:
                        app.logger.warning("Mapping rules content does not contain 'mapping_rules' key")

                    # Apply mapping rules immediately if available
                    if session_data['mapping_rules'] and sast_vulns:
                        auto_mappings = apply_mapping_rules_to_session(session_data)
                        session_data['confirmed_mappings'].extend(auto_mappings)
                        app.logger.info("Auto-applied {} mappings from uploaded rules".format(len(auto_mappings)))

                except Exception as e:
                    app.logger.warning("Failed to process mapping rules: " + str(e))
                    # Continue without mapping rules rather than failing the entire upload

            sessions[session_id] = session_data

            return jsonify({
                "session_id": session_id,
                "files_count": len(comparison.benchmark_vulns),
                "total_vulnerabilities": {
                    "benchmark": len(comparison.benchmark_vulns),
                    "sast": len(sast_vulns)
                }
            })

        except Exception as e:
            # Security: Log detailed errors server-side but don't leak sensitive info to client
            import traceback
            error_details = "File processing error: " + str(e) + "\n" + traceback.format_exc()
            app.logger.error(error_details)

            # Don't expose internal details to client
            if app.config.get('TESTING'):
                return jsonify({"error": "Test error: " + str(e)}), 500
            else:
                return jsonify({"error": "Failed to process uploaded files. Please check file format and try again."}), 500

    @app.route('/api/session/<session_id>', methods=['GET'])
    def get_session_data(session_id):
        """Get session vulnerability data grouped by files"""
        # Security: Validate session ID format
        if not SecurityValidator.validate_session_id(session_id):
            return jsonify({"error": "Invalid session ID format"}), 400

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
                "id": "bench_{}_{:06x}".format(idx, hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF),
                "file_path": vuln.file_path,
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
                "id": "sast_{}_{:06x}".format(idx, hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF),
                "file_path": vuln.file_path,
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
        # Security: CSRF Protection
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json and request.json.get('csrf_token'))
        if not csrf_token or csrf_token != session.get('csrf_token'):
            return jsonify({"error": "Invalid CSRF token"}), 403

        # Security: Validate session ID format
        if not SecurityValidator.validate_session_id(session_id):
            return jsonify({"error": "Invalid session ID format"}), 400

        if session_id not in app.sessions:
            return jsonify({"error": "Session not found"}), 404

        if not request.json:
            return jsonify({"error": "JSON data required"}), 400

        # Security: Validate and sanitize mapping request data
        try:
            data = SecurityValidator.validate_mapping_request(request.json)
        except ValueError as e:
            return jsonify({"error": "Invalid request data: " + str(e)}), 400

        action = data['action']
        benchmark_id = data['benchmark_id']
        sast_id = data['sast_id']

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

        # Initialize auto_mappings for all actions
        auto_mappings = []

        if action == 'confirm':
            session_data['confirmed_mappings'].append(mapping)

            # Create pattern rule for learning
            rule = create_pattern_rule(session_data, benchmark_id, sast_id)
            if rule:
                session_data['mapping_rules'].append(rule)

            # Auto-apply this rule to other similar SAST findings
            auto_mappings = apply_learned_rule(session_data, benchmark_id, sast_id)
            session_data['confirmed_mappings'].extend(auto_mappings)

        elif action == 'deny':
            session_data['denied_mappings'].append(mapping)

        # Generate new suggestions based on updated rules
        new_suggestions = generate_auto_suggestions(session_data)

        # Include info about auto-mapped findings
        auto_mapped_info = []
        if action == 'confirm' and auto_mappings:
            auto_mapped_info = [{"sast_id": m["sast_id"], "benchmark_id": m["benchmark_id"]} for m in auto_mappings]

        return jsonify({
            "success": True,
            "new_suggestions": new_suggestions,
            "auto_mapped": auto_mapped_info,
            "auto_mapped_count": len(auto_mappings)
        })

    @app.route('/api/session/<session_id>/suggestions', methods=['GET'])
    def get_suggestions(session_id):
        """Get auto-suggestions filtered by confidence threshold"""
        # Security: Validate session ID format
        if not SecurityValidator.validate_session_id(session_id):
            return jsonify({"error": "Invalid session ID format"}), 400

        if session_id not in app.sessions:
            return jsonify({"error": "Session not found"}), 404

        # Security: Validate confidence threshold
        try:
            confidence_raw = request.args.get('confidence', '50')
            confidence_threshold = SecurityValidator.validate_confidence_threshold(confidence_raw)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        session_data = app.sessions[session_id]

        # Use SastComparison to generate suggestions
        comparison = session_data['comparison']
        suggestions = comparison.generate_suggestions(session_data, confidence_threshold)

        # Build confidence scores summary
        confidence_scores = {}
        for suggestion in suggestions:
            score_range = "{}-{}".format((suggestion['confidence'] // 10) * 10, (suggestion['confidence'] // 10) * 10 + 9)
            confidence_scores[score_range] = confidence_scores.get(score_range, 0) + 1

        return jsonify({
            "suggestions": suggestions,
            "confidence_scores": confidence_scores
        })

    @app.route('/api/session/<session_id>/mappings', methods=['GET'])
    def get_session_mappings(session_id):
        """Get current session mappings for export as mapping rules.

        Returns:
            JSON containing confirmed and denied mappings in a format
            suitable for creating mapping rules files.
        """
        try:
            session_data = sessions.get(session_id)
            if not session_data:
                return jsonify({'error': 'Session not found'}), 404

            # Get confirmed and denied mappings from session
            confirmed_mappings = session_data.get('confirmed_mappings', [])
            denied_mappings = session_data.get('denied_mappings', [])

            # Build response with mappings in expected format
            response_data = {
                'mappings': confirmed_mappings + denied_mappings,
                'confirmed_count': len(confirmed_mappings),
                'denied_count': len(denied_mappings),
                'session_id': session_id
            }

            return jsonify(response_data)

        except Exception as e:
            app.logger.error("Failed to fetch session mappings for {}: {}".format(session_id, str(e)))
            return jsonify({'error': 'Failed to fetch mappings'}), 500

    @app.route('/api/session/<session_id>/export', methods=['GET'])
    def export_mapping(session_id):
        """Generate final mapping JSON for CLI tool compatibility.

        Exports in the format expected by sast_comparison.load_and_apply_mapping():
        {
            "matches": [(bench_dict, sast_dict), ...],
            "benchmark_only": [vuln_dict, ...],
            "sast_only": [vuln_dict, ...],
            "mapping_rules": [...],
            "statistics": {...}
        }
        """
        # Security: Validate session ID format
        if not SecurityValidator.validate_session_id(session_id):
            return jsonify({"error": "Invalid session ID format"}), 400

        if session_id not in app.sessions:
            return jsonify({"error": "Session not found"}), 404

        session_data = app.sessions[session_id]
        comparison = session_data['comparison']

        # Track which vulnerabilities have been matched
        matched_benchmark_ids = set()
        matched_sast_ids = set()

        # Build matches list with tuple format (bench_dict, sast_dict)
        matches = []
        for mapping in session_data.get('confirmed_mappings', []):
            benchmark_vuln = find_vulnerability_by_id(mapping['benchmark_id'], comparison.benchmark_vulns, 'bench')
            sast_vuln = find_vulnerability_by_id(mapping['sast_id'], session_data['sast_vulns'], 'sast')

            if benchmark_vuln and sast_vuln:
                bench_dict = {
                    'file_path': benchmark_vuln.file_path,
                    'line_number': benchmark_vuln.line_number,
                    'vuln_type': benchmark_vuln.vuln_type,
                    'severity': getattr(benchmark_vuln, 'severity', 'UNKNOWN'),
                    'description': getattr(benchmark_vuln, 'description', ''),
                    'source': getattr(benchmark_vuln, 'source', 'benchmark')
                }
                sast_dict = {
                    'file_path': sast_vuln.file_path,
                    'line_number': sast_vuln.line_number,
                    'vuln_type': sast_vuln.vuln_type,
                    'severity': getattr(sast_vuln, 'severity', 'UNKNOWN'),
                    'description': getattr(sast_vuln, 'description', ''),
                    'source': getattr(sast_vuln, 'source', 'sast')
                }
                matches.append([bench_dict, sast_dict])
                matched_benchmark_ids.add(mapping['benchmark_id'])
                matched_sast_ids.add(mapping['sast_id'])

        # Build benchmark_only list (unmatched benchmark vulnerabilities)
        benchmark_only = []
        for idx, vuln in enumerate(comparison.benchmark_vulns):
            vuln_id = "bench_{}_{:06x}".format(idx, hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF)
            if vuln_id not in matched_benchmark_ids:
                benchmark_only.append({
                    'file_path': vuln.file_path,
                    'line_number': vuln.line_number,
                    'vuln_type': vuln.vuln_type,
                    'severity': getattr(vuln, 'severity', 'UNKNOWN'),
                    'description': getattr(vuln, 'description', ''),
                    'source': getattr(vuln, 'source', 'benchmark')
                })

        # Build sast_only list (unmatched SAST vulnerabilities)
        sast_only = []
        for idx, vuln in enumerate(session_data['sast_vulns']):
            vuln_id = "sast_{}_{:06x}".format(idx, hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF)
            if vuln_id not in matched_sast_ids:
                sast_only.append({
                    'file_path': vuln.file_path,
                    'line_number': vuln.line_number,
                    'vuln_type': vuln.vuln_type,
                    'severity': getattr(vuln, 'severity', 'UNKNOWN'),
                    'description': getattr(vuln, 'description', ''),
                    'source': getattr(vuln, 'source', 'sast')
                })

        # Build CLI-compatible export format
        export_data = {
            'matches': matches,
            'benchmark_only': benchmark_only,
            'sast_only': sast_only,
            'mapping_rules': session_data.get('mapping_rules', []),
            'statistics': {
                'files_processed': len(set(v.file_path for v in comparison.benchmark_vulns)),
                'total_benchmark_vulns': len(comparison.benchmark_vulns),
                'total_sast_vulns': len(session_data['sast_vulns']),
                'matched_vulns': len(matches),
                'missed_by_sast': len(benchmark_only),
                'false_positives': len(sast_only)
            }
        }

        # Create downloadable response
        response = jsonify(export_data)
        response.headers['Content-Disposition'] = 'attachment; filename=vulnerability_mapping_{}.json'.format(session_id[:8])
        response.headers['Content-Type'] = 'application/json'

        return response

    @app.route('/', methods=['GET'])
    def serve_ui():
        """Serve the main vulnerability mapping interface"""
        return render_template('index.html')

    @app.route('/debug', methods=['GET'])
    def serve_debug():
        """Serve the upload debug interface"""
        return render_template('debug.html')

    @app.before_request
    def security_checks():
        """Perform security checks before processing requests"""
        cleanup_expired_sessions()

        # Rate limiting
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if not check_rate_limit(client_ip):
            return jsonify({"error": "Rate limit exceeded"}), 429

        # Block requests with suspicious headers (disabled for localhost development)
        if request.remote_addr not in ['127.0.0.1', '::1'] and check_suspicious_headers(request.headers):
            return jsonify({"error": "Request blocked"}), 400

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
        generated_id = "bench_{}_{:06x}".format(idx, hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF)
        if generated_id == benchmark_id:
            benchmark_vuln = vuln
            break

    sast_vuln = None
    for idx, vuln in enumerate(session_data['sast_vulns']):
        generated_id = "sast_{}_{:06x}".format(idx, hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF)
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
        generated_id = "{}_{}_{:06x}".format(vuln_type_prefix, idx, hash(vuln.file_path + str(vuln.line_number)) & 0xFFFFFF)
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


def apply_learned_rule(session_data, benchmark_id, sast_id):
    """Automatically apply learned mapping rule to other similar SAST findings"""
    auto_mappings = []

    # Get the SAST finding and benchmark vuln that was just mapped
    sast_vuln = find_vulnerability_by_id(sast_id, session_data['sast_vulns'], 'sast')
    benchmark_vuln = find_vulnerability_by_id(benchmark_id, session_data['comparison'].benchmark_vulns, 'bench')

    if not sast_vuln or not benchmark_vuln:
        return auto_mappings

    # Extract the SAST rule ID from the finding (stored in vuln_type for Semgrep)
    sast_rule_id = sast_vuln.vuln_type
    if not sast_rule_id:
        return auto_mappings

    print("🧠 Learning rule: {} -> {}".format(sast_rule_id, benchmark_vuln.vuln_type))

    # Find all other SAST findings with the same rule ID
    already_mapped = {m['sast_id'] for m in session_data.get('confirmed_mappings', [])}
    already_mapped.add(sast_id)  # Don't re-map the one we just confirmed

    print("🔧 Total SAST findings to check: {}".format(len(session_data['sast_vulns'])))
    print("🔧 Already mapped: {}".format(already_mapped))

    for idx, other_sast in enumerate(session_data['sast_vulns']):
        other_sast_id = "sast_{}_{:06x}".format(idx, hash(other_sast.file_path + str(other_sast.line_number)) & 0xFFFFFF)

        if other_sast_id in already_mapped:
            print("🔧 Skipping already mapped: {}".format(other_sast_id))
            continue

        # Check if this SAST finding has the same rule ID
        other_rule_id = other_sast.vuln_type
        print("🔧 Checking: {} rule '{}' == '{}'? {}".format(other_sast_id, other_rule_id, sast_rule_id, other_rule_id == sast_rule_id))

        if other_rule_id == sast_rule_id:
            # Find benchmark vulnerabilities of the same type in the same file
            for bench_idx, bench_vuln in enumerate(session_data['comparison'].benchmark_vulns):
                if (bench_vuln.file_path == other_sast.file_path and
                    bench_vuln.vuln_type == benchmark_vuln.vuln_type):

                    bench_id = "bench_{}_{:06x}".format(bench_idx, hash(bench_vuln.file_path + str(bench_vuln.line_number)) & 0xFFFFFF)

                    auto_mapping = {
                        "benchmark_id": bench_id,
                        "sast_id": other_sast_id,
                        "manual": False,  # This was auto-generated
                        "rule_learned_from": sast_rule_id,
                        "confidence": 95  # High confidence for rule-based mapping
                    }
                    auto_mappings.append(auto_mapping)
                    print("  ✅ Auto-mapped: {}:{} -> {}:{}".format(other_sast.file_path, other_sast.line_number, bench_vuln.file_path, bench_vuln.line_number))
                    break  # Only map to the best match per SAST finding

    print("🎯 Generated {} automatic mappings from learned rule".format(len(auto_mappings)))
    return auto_mappings


def generate_auto_suggestions(session_data):
    """Generate suggestions based on learned mapping rules"""
    suggestions = []

    # This could be enhanced to suggest mappings based on learned patterns
    # For now, return empty list - the main auto-mapping happens in apply_learned_rule

    return suggestions


def check_rate_limit(client_ip):
    """Check if client is within rate limits"""
    # Skip rate limiting for localhost/development
    if client_ip in ['127.0.0.1', 'localhost', '::1']:
        return True

    now = time.time()
    client_requests = rate_limits[client_ip]

    # Remove old requests outside the window
    while client_requests and client_requests[0] <= now - RATE_LIMIT_WINDOW:
        client_requests.popleft()

    # Check if limit exceeded
    if len(client_requests) >= MAX_REQUESTS_PER_MINUTE:
        return False

    # Add current request
    client_requests.append(now)
    return True


def check_suspicious_headers(headers):
    """Check for suspicious headers that might indicate an attack"""
    suspicious_patterns = [
        'eval(',
        'javascript:',
        'vbscript:',
        'data:',
        '<script',
        'onload=',
        'onerror=',
        'onclick=',
        'onfocus=',
        'onmouseover=',
        '%3Cscript',
        'document.cookie',
        'document.location',
        'window.location'
    ]

    for header_name, header_value in headers:
        if not isinstance(header_value, str):
            continue

        header_lower = header_value.lower()
        for pattern in suspicious_patterns:
            if pattern in header_lower:
                return True

        # Check for excessively long headers
        if len(header_value) > 8192:
            return True

    return False


def apply_mapping_rules_to_session(session_data):
    """Apply mapping rules to SAST vulnerabilities in a session"""
    auto_mappings = []
    mapping_rules = session_data.get('mapping_rules', {})

    if not mapping_rules or not session_data.get('sast_vulns'):
        return auto_mappings

    # Track which SAST findings have already been mapped
    already_mapped = {m['sast_id'] for m in session_data.get('confirmed_mappings', [])}

    for idx, sast_vuln in enumerate(session_data['sast_vulns']):
        sast_id = "sast_{}_{:06x}".format(idx, hash(sast_vuln.file_path + str(sast_vuln.line_number)) & 0xFFFFFF)

        if sast_id in already_mapped:
            continue

        # Check if any mapping rule matches this SAST vulnerability
        sast_rule_id = getattr(sast_vuln, 'vuln_type', '')
        if sast_rule_id in mapping_rules:
            rule_data = mapping_rules[sast_rule_id]

            # Find matching benchmark vulnerability
            for bench_idx, bench_vuln in enumerate(session_data['comparison'].benchmark_vulns):
                if (bench_vuln.file_path == sast_vuln.file_path and
                    bench_vuln.vuln_type == rule_data.get('benchmark_type')):

                    bench_id = "bench_{}_{:06x}".format(bench_idx, hash(bench_vuln.file_path + str(bench_vuln.line_number)) & 0xFFFFFF)

                    auto_mapping = {
                        "benchmark_id": bench_id,
                        "sast_id": sast_id,
                        "manual": False,
                        "auto_applied": True,
                        "rule_source": "uploaded_rules",
                        "confidence": 95
                    }
                    auto_mappings.append(auto_mapping)
                    already_mapped.add(sast_id)
                    break  # Only map to first match

    return auto_mappings

if __name__ == '__main__':
    app = create_app()
    # Debug disabled by default for security - only enable for troubleshooting
    # Set FLASK_DEBUG=1 environment variable to enable debug mode temporarily
    debug = os.environ.get('FLASK_DEBUG') == '1'

    # Default to production-safe settings
    host = os.environ.get('FLASK_HOST', '127.0.0.1')  # localhost by default
    port = int(os.environ.get('FLASK_PORT', '5001'))

    if debug:
        print("⚠️  WARNING: Debug mode is enabled! Only use for troubleshooting.")
        print("   Set FLASK_DEBUG=0 or unset FLASK_DEBUG for production.")
    else:
        print("✅ Running in production mode (debug disabled)")

    app.run(debug=debug, host=host, port=port)
