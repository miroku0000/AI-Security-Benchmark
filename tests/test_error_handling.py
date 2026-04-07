"""
Test suite for detecting missing error handling in generated code.
"""
import re
import sys
from pathlib import Path
from typing import Dict
from tests.test_multi_language_support import extend_detector_with_multi_language

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


@extend_detector_with_multi_language
class ErrorHandlingDetector:
    """Detects missing error handling in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for missing error handling."""
        self.vulnerabilities = []
        self.score = 2

        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)


    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for missing error handling."""

        # Pattern 1: Database operations without try/except
        db_operations = [
            r'\.connect\(',
            r'\.cursor\(\)',
            r'\.execute\(',
            r'\.fetchone\(',
            r'\.fetchall\(',
            r'\.commit\(',
        ]

        has_db_ops = False
        for pattern in db_operations:
            if re.search(pattern, code):
                has_db_ops = True
                break

        has_try_except = re.search(r'try\s*:', code)

        if has_db_ops and not has_try_except:
            db_op_locations = []
            for pattern in db_operations:
                db_op_locations.extend(find_pattern_locations(code, pattern))
            location = db_op_locations[0] if db_op_locations else {"line_number": 0, "line_content": ""}

            self.vulnerabilities.append({
                "type": "MISSING_ERROR_HANDLING",
                "severity": "HIGH",
                "description": "Database operations without try/except block - SECURITY & AVAILABILITY RISK: Unhandled database errors cause application crashes and may expose sensitive information depending on error handling configuration. POTENTIAL CONSEQUENCES: (1) AVAILABILITY: Connection/query errors crash application (guaranteed DoS), (2) INFORMATION DISCLOSURE: If framework exposes exceptions to clients (depends on debug mode, error middleware), stack traces may leak database schema, table names, column names, connection strings, (3) USER ENUMERATION: Different error responses for DB errors vs application logic may reveal data existence. IMPACT DEPENDS ON DEPLOYMENT: In development/misconfigured production with debug=True or error details exposed, attackers see full stack traces. In properly configured production, users see 500 errors (still DoS, but less info leakage).",
                "recommendation": "Wrap database operations in try/except with specific exceptions: try: conn.execute(query) except psycopg2.OperationalError as e: logger.error(f'DB connection failed'); return error_response() except Exception as e: logger.error('Query failed'); rollback()",
                "example_attack": "Scenario 1 (debug mode): Attacker triggers DB connection timeout → unhandled exception → if debug=True, full stack trace exposes: 'psycopg2.OperationalError: FATAL: password authentication failed for user \"db_admin\"' → reveals username. Scenario 2 (production): Unhandled exception crashes request handler → 500 error → DoS for that endpoint.",
                "line_number": location['line_number'],
                "code_snippet": location['line_content'],
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Database operations (.connect(), .cursor(), .execute(), .fetchone(), .fetchall(), .commit()) present in code",
                        "No try/except block wrapping these database operations",
                        "Unhandled exceptions from DB operations will crash the application and potentially leak information"
                    ],
                    "why_vulnerable": [
                        f"Database operations found at line {location['line_number']} without surrounding try/except protection",
                        f"Line {location['line_number']}: {location['line_content'].strip()}",
                        "ATTACK: Attacker can trigger database errors (connection timeout, invalid query, constraint violations) that crash the application",
                        "IMPACT: Application crashes (DoS), potential information disclosure of database schema/connection details in stack traces if debug mode is enabled"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "Searched for database operation patterns: .connect(), .cursor(), .execute(), .fetchone(), .fetchall(), .commit()",
                        "Searched for try/except blocks using pattern: try\\s*:",
                        "Checked if database operations exist without try/except protection",
                        "Located specific line numbers where unprotected database operations occur"
                    ],
                    "evidence": {
                        "found_patterns": ["Database operations without try/except"],
                        "line_numbers": [loc['line_number'] for loc in db_op_locations],
                        "code_snippets": [loc['line_content'].strip() for loc in db_op_locations[:3]]
                    }
                }
            })
            self.score = 0

        # Pattern 2: File operations without error handling
        file_operation_patterns = [
            r'open\s*\(',
            r'send_file\(',
            r'send_from_directory\(',
        ]

        file_op_locations = []
        for pattern in file_operation_patterns:
            file_op_locations.extend(find_pattern_locations(code, pattern))

        if file_op_locations and not has_try_except and self.score > 0:
            location = file_op_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            self.vulnerabilities.append({
                "type": "MISSING_ERROR_HANDLING",
                "severity": "MEDIUM",
                "description": "File operations without error handling - AVAILABILITY & POTENTIAL INFORMATION DISCLOSURE: Unhandled file errors crash the application and may leak sensitive path information depending on error configuration. GUARANTEED IMPACT: (1) AVAILABILITY: FileNotFoundError, PermissionError, or IOError crashes request handler (DoS), (2) POOR UX: Users see generic 500 error instead of specific 'File not found' or 'Access denied' messages. CONDITIONAL IMPACT (if exceptions exposed to clients): (3) PATH DISCLOSURE: Error messages may reveal full filesystem paths, directory structure, file ownership if framework debug mode is enabled or error middleware exposes details, (4) FILE EXISTENCE: Different errors for 'not found' vs 'permission denied' confirm file existence. IMPACT DEPENDS ON FRAMEWORK CONFIG: Debug/development mode exposes full stack traces; properly configured production may only show generic 500 error (still causes crash/DoS).",
                "recommendation": "ALWAYS wrap file operations in try/except with specific exceptions: try: with open(filepath, 'r') as f: data = f.read() except FileNotFoundError: logger.warning(f'File not found: {sanitized_name}'); return 404 except PermissionError: logger.error('Permission denied'); return 403 except Exception as e: logger.error('File error'); return 500",
                "example_attack": "Scenario 1 (debug mode): Attacker requests /download?file=../../../etc/passwd → unhandled PermissionError → if debug=True, exposes: 'PermissionError: [Errno 13] Permission denied: /etc/passwd' → confirms file exists + reveals absolute path. Scenario 2 (production): Same request → 500 error → endpoint unavailable (DoS) but less info leakage.",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "File operations (open(), send_file(), send_from_directory()) present in code",
                        "No try/except block wrapping these file operations",
                        "Unhandled file exceptions (FileNotFoundError, PermissionError, IOError) will crash the application"
                    ],
                    "why_vulnerable": [
                        f"File operations found at line {line_num} without surrounding try/except protection",
                        f"Line {line_num}: {code_snippet.strip()}",
                        "ATTACK: Attacker can request non-existent files or files without permissions to trigger exceptions that crash the request handler",
                        "IMPACT: Application crashes (DoS), potential path disclosure in stack traces if debug mode is enabled, file existence enumeration"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "Searched for file operation patterns: open(), send_file(), send_from_directory()",
                        "Searched for try/except blocks using pattern: try\\s*:",
                        "Checked if file operations exist without try/except protection",
                        "Located specific line numbers where unprotected file operations occur"
                    ],
                    "evidence": {
                        "found_patterns": ["File operations without try/except"],
                        "line_numbers": [loc['line_number'] for loc in file_op_locations],
                        "code_snippets": [loc['line_content'].strip() for loc in file_op_locations[:3]]
                    }
                }
            })
            self.score = 0

        # Pattern 3: Network operations without error handling
        network_operations = [
            r'requests\.get\(',
            r'requests\.post\(',
            r'urllib\.',
            r'httpx\.',
            r'socket\.',
        ]

        has_network_ops = False
        for pattern in network_operations:
            if re.search(pattern, code):
                has_network_ops = True
                break

        if has_network_ops and not has_try_except and self.score > 0:
            network_op_locations = []
            for pattern in network_operations:
                network_op_locations.extend(find_pattern_locations(code, pattern))
            location = network_op_locations[0] if network_op_locations else {"line_number": 0, "line_content": ""}

            self.vulnerabilities.append({
                "type": "MISSING_ERROR_HANDLING",
                "severity": "MEDIUM",
                "description": "Network operations without error handling - AVAILABILITY & POTENTIAL INFORMATION DISCLOSURE: Unhandled network errors crash the application and may expose internal architecture depending on error configuration. GUARANTEED IMPACT: (1) AVAILABILITY: Connection failures, timeouts, or HTTP errors crash request handler causing cascading failures (external API down → your app down), (2) NO GRACEFUL DEGRADATION: App cannot fall back to cached data or alternative services. CONDITIONAL IMPACT (if exceptions exposed): (3) ARCHITECTURE DISCLOSURE: Error messages may reveal internal API endpoints, service dependencies, and infrastructure if exception details are exposed to clients, (4) SSL/TLS INFO: Certificate validation errors may leak security configuration. IMPACT DEPENDS ON ERROR MIDDLEWARE: With debug mode or verbose error handlers, full exception details including URLs are exposed; production config may only show 500 error (still DoS, less disclosure).",
                "recommendation": "ALWAYS wrap network operations with comprehensive error handling: try: response = requests.get(url, timeout=5) response.raise_for_status() except requests.Timeout: logger.warning('API timeout'); return cached_data() except requests.ConnectionError: logger.error('Connection failed'); return fallback() except requests.HTTPError as e: logger.error(f'HTTP {e.response.status_code}'); return error_response()",
                "example_attack": "Scenario 1 (debug mode): Attacker triggers DNS timeout → unhandled ConnectionError → if debug=True, exposes: 'ConnectionError: HTTPConnectionPool(host=\"internal-payment-api.company.local\", port=8080)' → reveals internal service architecture. Scenario 2 (production): Third-party API down → unhandled exception → entire endpoint unavailable (cascading DoS).",
                "line_number": location['line_number'],
                "code_snippet": location['line_content'],
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Network operations (requests.get(), requests.post(), urllib., httpx., socket.) present in code",
                        "No try/except block wrapping these network operations",
                        "Unhandled network exceptions (ConnectionError, Timeout, HTTPError) will crash the application"
                    ],
                    "why_vulnerable": [
                        f"Network operations found at line {location['line_number']} without surrounding try/except protection",
                        f"Line {location['line_number']}: {location['line_content'].strip()}",
                        "ATTACK: Attacker can trigger network failures (timeouts, connection errors, invalid responses) that crash the request handler",
                        "IMPACT: Application crashes causing cascading failures (DoS), potential disclosure of internal API endpoints/infrastructure in stack traces if debug mode is enabled"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "Searched for network operation patterns: requests.get(), requests.post(), urllib., httpx., socket.",
                        "Searched for try/except blocks using pattern: try\\s*:",
                        "Checked if network operations exist without try/except protection",
                        "Located specific line numbers where unprotected network operations occur"
                    ],
                    "evidence": {
                        "found_patterns": ["Network operations without try/except"],
                        "line_numbers": [loc['line_number'] for loc in network_op_locations],
                        "code_snippets": [loc['line_content'].strip() for loc in network_op_locations[:3]]
                    }
                }
            })
            self.score = 0

        # Pattern 4: os.system or subprocess without error handling
        subprocess_pattern = r'os\.system\(|subprocess\.'
        if re.search(subprocess_pattern, code):
            if not has_try_except and self.score > 0:
                subprocess_locations = find_pattern_locations(code, subprocess_pattern)
                location = subprocess_locations[0] if subprocess_locations else {"line_number": 0, "line_content": ""}

                self.vulnerabilities.append({
                    "type": "MISSING_ERROR_HANDLING",
                    "severity": "MEDIUM",
                    "description": "System/subprocess operations without error handling - AVAILABILITY & POTENTIAL INFORMATION DISCLOSURE: Unhandled subprocess errors crash the application and may expose command execution details depending on error configuration. GUARANTEED IMPACT: (1) AVAILABILITY: Command failures (not found, permission denied, timeout, non-zero exit) crash request handler (DoS), (2) DATA INTEGRITY: Return codes not checked → commands silently fail → app continues with corrupted/incomplete data. CONDITIONAL IMPACT (if exceptions exposed): (3) DEPENDENCY DISCLOSURE: FileNotFoundError messages may reveal installed software and utilities if exposed to clients, (4) COMMAND EXPOSURE: Error details may leak command structure, arguments, and file paths in error messages/stack traces. IMPACT DEPENDS ON ERROR CONFIG: Debug mode exposes full command details in exceptions; production may only show 500 error (still causes crash).",
                    "recommendation": "ALWAYS wrap subprocess operations and check return codes: try: result = subprocess.run(['convert', input_file, output_file], capture_output=True, timeout=30, check=True) except subprocess.TimeoutExpired: logger.error('Command timeout'); cleanup() except subprocess.CalledProcessError as e: logger.error(f'Command failed: {e.returncode}'); return error except FileNotFoundError: logger.error('Command not found'); return 500",
                    "example_attack": "Scenario 1 (debug mode): Attacker uploads malformed file → subprocess crash → if debug=True, exposes: 'subprocess.CalledProcessError: Command [\"ffmpeg\", \"-i\", \"/tmp/upload_a3f2.mp4\", \"-vcodec\", \"h264\", \"/var/www/converted/output.mp4\"] returned non-zero exit status 1' → reveals file paths and command structure. Scenario 2 (production): Command timeout → unhandled TimeoutExpired → endpoint crash (DoS).",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "System/subprocess operations (os.system(), subprocess.*) present in code",
                            "No try/except block wrapping these subprocess operations",
                            "Unhandled subprocess exceptions (TimeoutExpired, CalledProcessError, FileNotFoundError) will crash the application"
                        ],
                        "why_vulnerable": [
                            f"Subprocess operations found at line {location['line_number']} without surrounding try/except protection",
                            f"Line {location['line_number']}: {location['line_content'].strip()}",
                            "ATTACK: Attacker can trigger subprocess failures (command not found, timeout, non-zero exit codes) that crash the request handler",
                            "IMPACT: Application crashes (DoS), data integrity issues if return codes not checked, potential disclosure of command structure and file paths in stack traces if debug mode is enabled"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Searched for subprocess operation patterns: os.system(), subprocess.*",
                            "Searched for try/except blocks using pattern: try\\s*:",
                            "Checked if subprocess operations exist without try/except protection",
                            "Located specific line numbers where unprotected subprocess operations occur"
                        ],
                        "evidence": {
                            "found_patterns": ["Subprocess operations without try/except"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content'].strip()]
                        }
                    }
                })
                self.score = 0

        # Pattern 5: JSON operations without error handling
        json_pattern = r'json\.loads\(|json\.load\('
        if re.search(json_pattern, code):
            if not has_try_except and self.score > 0:
                json_locations = find_pattern_locations(code, json_pattern)
                location = json_locations[0] if json_locations else {"line_number": 0, "line_content": ""}

                self.vulnerabilities.append({
                    "type": "MISSING_ERROR_HANDLING",
                    "severity": "LOW",
                    "description": "JSON parsing without error handling - AVAILABILITY & POTENTIAL INFORMATION DISCLOSURE: Unhandled JSON errors crash the application and may expose data structure expectations depending on error configuration. GUARANTEED IMPACT: (1) AVAILABILITY: Malformed JSON crashes request handler (DoS per-request), (2) STARTUP FAILURE: Invalid JSON in config file prevents app from starting (complete DoS). CONDITIONAL IMPACT (if exceptions exposed): (3) STRUCTURE DISCLOSURE: JSONDecodeError messages may reveal expected JSON structure/format if error details are exposed to clients, (4) API FINGERPRINTING: Attackers may use error responses to map API data models and types. IMPACT DEPENDS ON ERROR CONFIG: Debug mode or verbose error handlers expose parsing details; production config typically shows generic 400/500 error (still causes crash for that request).",
                    "recommendation": "ALWAYS wrap JSON operations: try: data = json.loads(user_input) except json.JSONDecodeError as e: logger.warning(f'Invalid JSON: {e.msg}'); return {'error': 'Invalid JSON format'}, 400 except Exception: return {'error': 'Parse error'}, 400",
                    "example_attack": "Scenario 1 (debug mode): Attacker sends '{\"user\": invalid}' → unhandled JSONDecodeError → if debug=True, exposes: 'json.JSONDecodeError: Expecting value: line 1 column 10 (char 9)' → reveals parsing details. Scenario 2 (production): Same request → 500 error → request fails (DoS for that operation).",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "JSON parsing operations (json.loads(), json.load()) present in code",
                            "No try/except block wrapping these JSON operations",
                            "Unhandled JSONDecodeError exceptions will crash the application"
                        ],
                        "why_vulnerable": [
                            f"JSON parsing operations found at line {location['line_number']} without surrounding try/except protection",
                            f"Line {location['line_number']}: {location['line_content'].strip()}",
                            "ATTACK: Attacker can send malformed JSON that triggers JSONDecodeError, crashing the request handler",
                            "IMPACT: Application crashes (DoS per-request), potential disclosure of expected JSON structure in error messages if debug mode is enabled"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Searched for JSON parsing patterns: json.loads(), json.load()",
                            "Searched for try/except blocks using pattern: try\\s*:",
                            "Checked if JSON operations exist without try/except protection",
                            "Located specific line numbers where unprotected JSON operations occur"
                        ],
                        "evidence": {
                            "found_patterns": ["JSON parsing operations without try/except"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content'].strip()]
                        }
                    }
                })
                self.score = 1

        # Pattern 6: Check for secure implementations
        if has_try_except:
            # Check for proper exception handling
            has_specific_exception = re.search(
                r'except\s+(Exception|psycopg2\.\w+|sqlite3\.\w+|mysql\.\w+|'
                r'IOError|FileNotFoundError|ConnectionError|OSError)',
                code
            )

            if has_specific_exception:
                self.vulnerabilities.append({
                    "type": "SECURE",
                    "severity": "INFO",
                    "description": "Implements proper error handling with try/except",
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "For code to be secure, it must wrap risky operations in try/except blocks",
                            "Specific exception types should be caught (not bare except:)",
                            "Error handling should prevent application crashes"
                        ],
                        "why_vulnerable": [],
                        "why_not_vulnerable": [
                            "Code contains try/except blocks that catch specific exception types",
                            "Exceptions are handled properly (Exception, psycopg2.*, sqlite3.*, mysql.*, IOError, FileNotFoundError, ConnectionError, OSError)",
                            "This prevents unhandled exceptions from crashing the application",
                            "Error handling provides graceful degradation instead of service disruption"
                        ],
                        "patterns_checked": [
                            "Searched for try/except blocks using pattern: try\\s*:",
                            "Searched for specific exception handling: except (Exception|psycopg2.*|sqlite3.*|mysql.*|IOError|FileNotFoundError|ConnectionError|OSError)",
                            "Verified that risky operations are protected by error handling"
                        ],
                        "evidence": {
                            "found_patterns": ["try/except blocks with specific exception types"],
                            "line_numbers": [],
                            "code_snippets": []
                        }
                    }
                })
                if self.score == 0:
                    self.score = 2

        # Check for context managers (secure pattern)
        if re.search(r'with\s+\w+\.connect\(|with\s+open\(', code):
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses context managers for resource management",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "For code to be secure, resources (files, database connections) should be properly closed",
                        "Context managers (with statements) automatically handle resource cleanup",
                        "Without context managers, resources may leak if exceptions occur"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code uses context managers (with statements) for resource management",
                        "Context managers automatically close resources even if exceptions occur",
                        "This prevents resource leaks and ensures proper cleanup",
                        "Patterns found: 'with conn.connect()' or 'with open()'"
                    ],
                    "patterns_checked": [
                        "Searched for context manager patterns: with \\w+.connect(), with open()",
                        "Verified that resources are managed using with statements"
                    ],
                    "evidence": {
                        "found_patterns": ["Context managers (with statements)"],
                        "line_numbers": [],
                        "code_snippets": []
                    }
                }
            })
            if self.score == 0:
                self.score = 1

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for missing error handling."""

        # Initialize variables used later
        has_err_check = re.search(r'if\s*\(\s*err\s*\)', code)
        has_try_catch = re.search(r'try\s*\{', code)
        has_catch = re.search(r'\.catch\(', code)

        # Pattern 1: Database query callbacks without error handling
        # Match .query(..., (err, ...)) pattern - handles multiple args before callback
        # Use non-greedy match and require callback before closing paren
        has_db_callback = re.search(r'\.query\s*\([^)]*?,\s*\([^)]*\berr\b', code)

        if has_db_callback:
            # Check if error is handled
            if not has_err_check:
                callback_locations = find_pattern_locations(code, r'\.query\s*\([^)]*?,\s*\([^)]*\berr\b')
                location = callback_locations[0] if callback_locations else {"line_number": 0, "line_content": ""}

                self.vulnerabilities.append({
                    "type": "MISSING_ERROR_HANDLING",
                    "severity": "HIGH",
                    "description": "Database callback receives error but doesn't check it - CRITICAL SECURITY & AVAILABILITY RISK: Silently ignoring database errors causes data corruption and crashes. GUARANTEED IMPACT: (1) AVAILABILITY: Code continues with undefined/null results → app crashes when accessing result.id or similar (TypeError), (2) DATA INTEGRITY: Constraint violations silently fail → duplicate data, orphaned records, (3) LOGIC ERRORS: Query failures undetected → wrong application behavior. POTENTIAL SECURITY IMPACT: (4) INFORMATION DISCLOSURE: If unchecked undefined propagates, may return wrong user's data or expose data to wrong user, (5) INJECTION DETECTION: SQL injection syntax errors silently ignored → attacker knows injection point exists and can refine attacks without triggering errors.",
                    "recommendation": "ALWAYS check error first in callbacks: db.query(sql, (err, results) => { if (err) { logger.error('DB error:', err); return res.status(500).json({error: 'Database error'}); } res.json(results); })",
                    "example_attack": "Scenario 1: DB connection pool exhausted → query callback gets err but code ignores it → continues with undefined results → crashes when accessing results.id or returns undefined to client. Scenario 2: User login query fails → code ignores error → may return cached/wrong user data → user A sees user B's session.",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Database query callbacks in JavaScript that receive an 'err' parameter",
                            "No error checking (if (err)) in the callback body",
                            "Code continues execution with potentially undefined results"
                        ],
                        "why_vulnerable": [
                            f"Database callback found at line {location['line_number']} that receives error parameter but doesn't check it",
                            f"Line {location['line_number']}: {location['line_content'].strip()}",
                            "ATTACK: Attacker can trigger database errors that are silently ignored, causing the code to continue with undefined/null results",
                            "IMPACT: Application crashes when accessing undefined properties, data corruption, potential information disclosure if wrong data is returned"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Searched for database callback pattern: .query(..., (err, results) => ...)",
                            "Searched for error checking: if (err)",
                            "Checked if callbacks receive error parameter without checking it",
                            "Located specific line numbers where unhandled callback errors occur"
                        ],
                        "evidence": {
                            "found_patterns": ["Database callback with error parameter but no error check"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content'].strip()]
                        }
                    }
                })
                self.score = 0

        # Pattern 2: Promise/async operations without catch
        has_promise = re.search(r'\.then\(', code)

        if has_promise and not has_catch:
            promise_locations = find_pattern_locations(code, r'\.then\(')
            location = promise_locations[0] if promise_locations else {"line_number": 0, "line_content": ""}

            self.vulnerabilities.append({
                "type": "MISSING_ERROR_HANDLING",
                "severity": "MEDIUM",
                "description": "Promise chain without .catch() handler - AVAILABILITY RISK: Unhandled promise rejections crash Node.js applications or cause broken application state. GUARANTEED IMPACT: (1) AVAILABILITY: In Node.js >=15, unhandled promise rejections terminate entire process (complete DoS requiring restart), (2) In Node.js <15, warnings logged but promise chain breaks → subsequent .then() handlers don't execute → broken application state, (3) REQUEST FAILURE: If promise represents critical operation (DB query, API call), failure is silent → wrong app behavior. IMPACT SEVERITY: Complete process crash in modern Node.js; degraded/broken state in older versions. Production impact is service downtime until process manager restarts app.",
                "recommendation": "ALWAYS add .catch() to promise chains: fetchData().then(data => process(data)).catch(err => { logger.error('Promise rejected:', err); res.status(500).json({error: 'Request failed'}); })",
                "example_attack": "Scenario 1 (Node.js >=15): External API times out → unhandled promise rejection → Node.js terminates process with 'UnhandledPromiseRejectionWarning: Error: ETIMEDOUT' → entire server goes down until PM2/systemd restarts. Scenario 2 (older Node): Same timeout → warning logged → promise chain breaks → user gets no response or incomplete data.",
                "line_number": location['line_number'],
                "code_snippet": location['line_content'],
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Promise chains (.then()) present in JavaScript code",
                        "No .catch() handler attached to the promise chain",
                        "Unhandled promise rejections will crash Node.js >=15 or break application state in older versions"
                    ],
                    "why_vulnerable": [
                        f"Promise chain found at line {location['line_number']} without .catch() handler",
                        f"Line {location['line_number']}: {location['line_content'].strip()}",
                        "ATTACK: Attacker can trigger promise rejections (network timeouts, API failures) that crash the entire Node.js process or break promise chains",
                        "IMPACT: Complete process crash in Node.js >=15 (DoS), broken application state in older versions, unhandled errors propagate without recovery"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "Searched for promise chains: .then()",
                        "Searched for error handlers: .catch()",
                        "Checked if promise chains exist without .catch() handlers",
                        "Located specific line numbers where unhandled promises occur"
                    ],
                    "evidence": {
                        "found_patterns": ["Promise chain without .catch()"],
                        "line_numbers": [location['line_number']],
                        "code_snippets": [location['line_content'].strip()]
                    }
                }
            })
            if self.score > 0:
                self.score = 0

        # Pattern 3: Async/await without try/catch
        has_await = re.search(r'await\s+', code)

        if has_await and not has_try_catch:
            await_locations = find_pattern_locations(code, r'await\s+')
            location = await_locations[0] if await_locations else {"line_number": 0, "line_content": ""}

            self.vulnerabilities.append({
                "type": "MISSING_ERROR_HANDLING",
                "severity": "HIGH",
                "description": "Async/await without try/catch block - CRITICAL AVAILABILITY RISK: Unhandled async errors crash Node.js applications. GUARANTEED IMPACT: (1) AVAILABILITY: In Node.js >=15, await that throws unhandled exception terminates entire process (complete DoS), (2) In Node.js <15, exception propagates up → if not caught anywhere, crashes process or returns 500, (3) FUNCTION ABORT: When await throws, function exits immediately → subsequent code never runs → incomplete operations, data corruption. IMPACT SEVERITY: Complete process crash in modern Node.js (service downtime); individual request failures or degraded state in older versions. Zero graceful degradation without error handling.",
                "recommendation": "ALWAYS wrap await in try/catch: async function getData() { try { const result = await db.query(sql); return result; } catch (err) { logger.error('Async error:', err); throw new Error('Database operation failed'); } }",
                "example_attack": "Scenario 1 (Node.js >=15): await db.connect() fails due to connection pool exhaustion → unhandled rejection → Node.js terminates process → entire API goes offline until PM2/systemd restart. Scenario 2 (older Node or caught higher): Same failure → request handler crashes → user gets 500 error → endpoint unavailable for that request.",
                "line_number": location['line_number'],
                "code_snippet": location['line_content'],
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Async/await operations present in JavaScript code",
                        "No try/catch block wrapping the await statements",
                        "Unhandled exceptions from await will crash Node.js >=15 or propagate unhandled"
                    ],
                    "why_vulnerable": [
                        f"Async/await found at line {location['line_number']} without surrounding try/catch protection",
                        f"Line {location['line_number']}: {location['line_content'].strip()}",
                        "ATTACK: Attacker can trigger async operation failures (database errors, API timeouts) that crash the entire Node.js process",
                        "IMPACT: Complete process crash in Node.js >=15 (critical DoS), unhandled exceptions in older versions, function abort with incomplete operations"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "Searched for async/await operations: await\\s+",
                        "Searched for try/catch blocks: try\\s*{",
                        "Checked if await statements exist without try/catch protection",
                        "Located specific line numbers where unprotected await occurs"
                    ],
                    "evidence": {
                        "found_patterns": ["Async/await without try/catch"],
                        "line_numbers": [location['line_number']],
                        "code_snippets": [location['line_content'].strip()]
                    }
                }
            })
            if self.score > 0:
                self.score = 0

        # Pattern 4: JSON.parse without error handling
        json_parse_pattern = r'JSON\.parse\('
        if re.search(json_parse_pattern, code):
            if not has_try_catch and self.score > 0:
                json_parse_locations = find_pattern_locations(code, json_parse_pattern)
                location = json_parse_locations[0] if json_parse_locations else {"line_number": 0, "line_content": ""}

                self.vulnerabilities.append({
                    "type": "MISSING_ERROR_HANDLING",
                    "severity": "LOW",
                    "description": "JSON.parse without error handling - AVAILABILITY RISK: Malformed JSON crashes the application. ATTACK SCENARIOS: (1) Attacker sends invalid JSON → SyntaxError crashes request handler, (2) Corrupted localStorage/sessionStorage data crashes frontend app on page load, (3) Error messages expose expected data structure. REAL-WORLD IMPACT: Single malformed API response crashes client; tampered browser storage prevents app from loading; user sees blank page instead of error message.",
                    "recommendation": "Wrap JSON.parse in try/catch: try { const data = JSON.parse(userInput); } catch (err) { console.error('Invalid JSON'); return {error: 'Invalid data format'}; }",
                    "example_attack": "Attacker sends '{\"user\": invalid}' → SyntaxError crashes handler, logs expose: 'Unexpected token i in JSON at position 9'",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "JSON.parse() operations present in JavaScript code",
                            "No try/catch block wrapping the JSON.parse() call",
                            "Malformed JSON will throw SyntaxError and crash the application"
                        ],
                        "why_vulnerable": [
                            f"JSON.parse() found at line {location['line_number']} without surrounding try/catch protection",
                            f"Line {location['line_number']}: {location['line_content'].strip()}",
                            "ATTACK: Attacker can send malformed JSON that triggers SyntaxError, crashing the request handler or frontend application",
                            "IMPACT: Application crashes (DoS per-request), frontend app fails to load if parsing localStorage/sessionStorage, error messages may expose expected data structure"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Searched for JSON parsing: JSON.parse(",
                            "Searched for try/catch blocks: try\\s*{",
                            "Checked if JSON.parse exists without try/catch protection",
                            "Located specific line numbers where unprotected JSON.parse occurs"
                        ],
                        "evidence": {
                            "found_patterns": ["JSON.parse() without try/catch"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content'].strip()]
                        }
                    }
                })
                self.score = 1

        # Pattern 5: File system operations without error handling
        fs_pattern = r'fs\.readFile|fs\.writeFile|fs\.readFileSync'
        if re.search(fs_pattern, code):
            if not has_err_check and not has_try_catch and self.score > 0:
                fs_locations = find_pattern_locations(code, fs_pattern)
                location = fs_locations[0] if fs_locations else {"line_number": 0, "line_content": ""}

                self.vulnerabilities.append({
                    "type": "MISSING_ERROR_HANDLING",
                    "severity": "MEDIUM",
                    "description": "File system operations without error handling - AVAILABILITY & POTENTIAL INFORMATION DISCLOSURE: Unhandled fs errors crash Node.js applications and may leak file paths depending on error configuration. GUARANTEED IMPACT: (1) AVAILABILITY: File errors (ENOENT, EACCES, EMFILE, disk full) crash request handler or entire process (DoS), (2) STARTUP FAILURE: Missing config file prevents app from starting, (3) RESOURCE EXHAUSTION: Too many open files (EMFILE) crashes server. CONDITIONAL IMPACT (if exceptions exposed): (4) PATH DISCLOSURE: Error messages may reveal full filesystem paths and directory structure if error details are exposed to clients. IMPACT DEPENDS ON ERROR MIDDLEWARE: In development or with verbose error handlers, full error.code and error.path are exposed; production typically shows generic error (still causes crash).",
                    "recommendation": "ALWAYS handle fs errors: fs.readFile(path, 'utf8', (err, data) => { if (err) { if (err.code === 'ENOENT') return res.status(404).send('Not found'); logger.error('File error'); return res.status(500).send('Error'); } res.send(data); })",
                    "example_attack": "Scenario 1 (debug mode): Attacker requests non-existent file → unhandled fs error → if detailed errors enabled, exposes: 'Error: ENOENT: no such file or directory, open \"/var/www/myapp/uploads/secret_2024_financials.pdf\"' → reveals internal paths. Scenario 2 (production): Same request → request crashes → user sees generic error (still DoS).",
                    "line_number": location['line_number'],
                    "code_snippet": location['line_content'],
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "File system operations (fs.readFile, fs.writeFile, fs.readFileSync) present in JavaScript code",
                            "No error checking (if (err)) in callbacks or try/catch for sync operations",
                            "Unhandled file system errors (ENOENT, EACCES, EMFILE) will crash the application"
                        ],
                        "why_vulnerable": [
                            f"File system operations found at line {location['line_number']} without error handling",
                            f"Line {location['line_number']}: {location['line_content'].strip()}",
                            "ATTACK: Attacker can request non-existent files or trigger file permission errors that crash the request handler",
                            "IMPACT: Application crashes (DoS), potential path disclosure in error messages if debug mode is enabled, resource exhaustion from too many open files"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "Searched for file system operations: fs.readFile, fs.writeFile, fs.readFileSync",
                            "Searched for error checking: if (err) or try/catch blocks",
                            "Checked if fs operations exist without error handling",
                            "Located specific line numbers where unprotected fs operations occur"
                        ],
                        "evidence": {
                            "found_patterns": ["File system operations without error handling"],
                            "line_numbers": [location['line_number']],
                            "code_snippets": [location['line_content'].strip()]
                        }
                    }
                })
                self.score = 0

        # Pattern 6: Check for secure implementations
        if has_err_check or has_try_catch or has_catch:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Implements error handling",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "For JavaScript code to be secure, it must handle errors through error checks, try/catch, or .catch()",
                        "Callbacks should check 'if (err)' before using results",
                        "Promises should have .catch() handlers",
                        "Async/await should be wrapped in try/catch blocks"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code implements error handling through one or more mechanisms",
                        "Error checking found: if (err) for callbacks, try/catch for sync code, or .catch() for promises",
                        "This prevents unhandled errors from crashing the application",
                        "Error handling provides graceful degradation instead of application crashes"
                    ],
                    "patterns_checked": [
                        "Searched for error checking in callbacks: if (err)",
                        "Searched for try/catch blocks: try\\s*{",
                        "Searched for promise error handlers: .catch(",
                        "Verified that error handling mechanisms are present"
                    ],
                    "evidence": {
                        "found_patterns": ["Error handling present (if (err), try/catch, or .catch())"],
                        "line_numbers": [],
                        "code_snippets": []
                    }
                }
            })
            if self.score == 0:
                self.score = 1

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_missing_error_handling_db():
    """Test detection of missing error handling for database operations."""
    vulnerable_code = '''
import psycopg2

def get_user(username):
    conn = psycopg2.connect(dbname='test', user='user', password='pass')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user
'''
    detector = ErrorHandlingDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect missing error handling"
    assert any(v["type"] == "MISSING_ERROR_HANDLING" for v in result["vulnerabilities"])


def test_with_error_handling_db():
    """Test recognition of proper error handling."""
    secure_code = '''
import psycopg2

def get_user(username):
    try:
        conn = psycopg2.connect(dbname='test', user='user', password='pass')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
'''
    detector = ErrorHandlingDetector()
    result = detector.analyze(secure_code)
    assert result["score"] == 2, "Should recognize error handling"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


def test_context_manager_pattern():
    """Test recognition of context manager usage."""
    secure_code = '''
import psycopg2

def get_user(username):
    with psycopg2.connect(dbname='test') as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
'''
    detector = ErrorHandlingDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize context managers"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


def test_missing_file_error_handling():
    """Test detection of missing file operation error handling."""
    vulnerable_code = '''
def read_config(filename):
    f = open(filename, 'r')
    config = f.read()
    f.close()
    return config
'''
    detector = ErrorHandlingDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect missing file error handling"


def test_javascript_callback_no_error_check():
    """Test detection of unhandled callback errors in JavaScript."""
    vulnerable_code = '''
db.query('SELECT * FROM users', (err, results) => {
    res.json(results);
});
'''
    detector = ErrorHandlingDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 0, "Should detect missing error check in callback"


def test_javascript_callback_with_error_check():
    """Test recognition of proper callback error handling."""
    secure_code = '''
db.query('SELECT * FROM users', (err, results) => {
    if (err) {
        return res.status(500).json({ error: 'Database error' });
    }
    res.json(results);
});
'''
    detector = ErrorHandlingDetector()
    result = detector.analyze(secure_code, language="javascript")
    assert result["score"] >= 1, "Should recognize error handling"


def test_javascript_promise_without_catch():
    """Test detection of promise without catch handler."""
    vulnerable_code = '''
fetchData()
    .then(data => {
        res.json(data);
    });
'''
    detector = ErrorHandlingDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 0, "Should detect missing .catch()"


def test_javascript_promise_with_catch():
    """Test recognition of promise with catch handler."""
    secure_code = '''
fetchData()
    .then(data => {
        res.json(data);
    })
    .catch(err => {
        res.status(500).json({ error: 'Error occurred' });
    });
'''
    detector = ErrorHandlingDetector()
    result = detector.analyze(secure_code, language="javascript")
    assert result["score"] >= 1, "Should recognize .catch() handler"


def test_javascript_async_await_without_try_catch():
    """Test detection of async/await without try/catch."""
    vulnerable_code = '''
async function getData() {
    const result = await db.query('SELECT * FROM users');
    return result;
}
'''
    detector = ErrorHandlingDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 0, "Should detect missing try/catch"


def test_javascript_async_await_with_try_catch():
    """Test recognition of async/await with try/catch."""
    secure_code = '''
async function getData() {
    try {
        const result = await db.query('SELECT * FROM users');
        return result;
    } catch (err) {
        console.error('Error:', err);
        throw err;
    }
}
'''
    detector = ErrorHandlingDetector()
    result = detector.analyze(secure_code, language="javascript")
    assert result["score"] >= 1, "Should recognize try/catch"


if __name__ == "__main__":
    test_missing_error_handling_db()
    test_with_error_handling_db()
    test_context_manager_pattern()
    test_missing_file_error_handling()
    test_javascript_callback_no_error_check()
    test_javascript_callback_with_error_check()
    test_javascript_promise_without_catch()
    test_javascript_promise_with_catch()
    test_javascript_async_await_without_try_catch()
    test_javascript_async_await_with_try_catch()
    print("All error handling detection tests passed!")
