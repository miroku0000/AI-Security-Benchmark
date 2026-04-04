"""
Test suite for detecting resource leaks in generated code.
"""
import re
import sys
from pathlib import Path
from typing import Dict

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class ResourceLeakDetector:
    """Detects resource leaks (unclosed connections, files, etc.) in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for resource leaks."""
        self.vulnerabilities = []
        self.score = 2

        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"]}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for resource leaks."""

        # Pattern 1: Database connections without proper cleanup
        connect_locations = find_pattern_locations(code, r'(\w+)\s*=\s*\w*\.?connect\s*\(')
        has_db_close = re.search(r'\.close\s*\(\)', code)
        has_context_manager = re.search(r'with\s+\w+\.connect\(', code)
        has_try_finally = re.search(r'try\s*:.*finally\s*:', code, re.DOTALL)

        if connect_locations and not has_context_manager:
            # Extract connection variable name
            location = connect_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            # Try to extract variable name
            var_match = re.search(r'(\w+)\s*=.*\.connect\s*\(', code_snippet)
            var_name = var_match.group(1) if var_match else "connection"

            # Check if this specific connection is closed
            close_pattern = f'{var_name}\\.close\\s*\\(\\)'
            _ = re.search(close_pattern, code)

            # Check if close is called
            if not has_db_close:
                self.vulnerabilities.append({
                    "type": "RESOURCE_LEAK",
                    "severity": "HIGH",
                    "description": f"Database connection '{var_name}' opened but never closed - will leak connection on every call, leading to connection pool exhaustion and application failure",
                    "recommendation": "Use 'with' statement or call .close() in finally block",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Database connections are limited resources that must be explicitly closed",
                            "Unclosed connections remain open, consuming database server resources",
                            "Connection pools have finite size - leaked connections cause pool exhaustion"
                        ],
                        "why_vulnerable": [
                            f"Database connection '{var_name}' is opened but .close() is never called",
                            f"Line {line_num}: {code_snippet}",
                            "ATTACK: Call this function repeatedly (e.g., 100 concurrent requests) → Each call opens new connection without closing → Connection pool exhausted within seconds → New requests fail with 'too many connections' error → Application becomes unresponsive",
                            "IMPACT: Resource exhaustion, application downtime, denial of service. Database refuses new connections, causing cascading failures across application."
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "*.connect() - Database connection opened",
                            ".close() - Connection cleanup (not found)",
                            "with *.connect() - Context manager (not found)",
                            "try/finally with .close() - Guaranteed cleanup (not found)"
                        ],
                        "evidence": {
                            "found_patterns": [f"{var_name} = *.connect() without .close()"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0
            elif has_db_close and not has_try_finally:
                # Close exists but not in finally block
                self.vulnerabilities.append({
                    "type": "RESOURCE_LEAK",
                    "severity": "MEDIUM",
                    "description": f"Database connection '{var_name}' not guaranteed to close on error - if exception occurs before .close(), connection will leak and not be returned to pool",
                    "recommendation": "Use 'with' statement or put .close() in finally block",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Connection cleanup must be guaranteed even when exceptions occur",
                            ".close() in normal code path may not execute if exception is raised",
                            "Proper cleanup requires try/finally block or context manager"
                        ],
                        "why_vulnerable": [
                            f"Connection '{var_name}' has .close() call but not in finally block",
                            f"Line {line_num}: {code_snippet}",
                            "ATTACK: Provide invalid input that triggers exception (e.g., SQL error, validation error) → Exception raised before .close() → Connection never closed → Repeated attacks leak connections → Pool exhaustion",
                            "IMPACT: Resource leak on error conditions. Under error scenarios or attacks that trigger exceptions, connections leak steadily until pool exhaustion causes application failure."
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "*.connect() - Database connection",
                            ".close() - Cleanup exists but may not execute",
                            "try/finally - Guaranteed cleanup (not found)",
                            "with statement - Automatic cleanup (not found)"
                        ],
                        "evidence": {
                            "found_patterns": [f"{var_name}.close() without try/finally"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                if self.score > 1:
                    self.score = 1

        # Pattern 2: Cursors not properly closed
        cursor_locations = find_pattern_locations(code, r'(\w+)\s*=\s*\w+\.cursor\s*\(\)')
        has_cursor_context = re.search(r'with\s+.*\.cursor\(', code)

        if cursor_locations and not has_cursor_context:
            location = cursor_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            # Extract cursor variable name
            var_match = re.search(r'(\w+)\s*=', code_snippet)
            var_name = var_match.group(1) if var_match else "cursor"

            # IMPROVED: Check if cursor is inside a connection context manager
            # If connection uses 'with', cursor cleanup is often handled automatically
            lines = code.split('\n')
            cursor_line_idx = line_num - 1

            # Look backwards for 'with' statement that might cover this cursor
            in_connection_context = False
            for i in range(max(0, cursor_line_idx - 10), cursor_line_idx):
                if re.search(r'with\s+.*\.connect\(', lines[i]):
                    # Check if cursor is indented relative to 'with' (inside its block)
                    with_indent = len(lines[i]) - len(lines[i].lstrip())
                    cursor_indent = len(lines[cursor_line_idx]) - len(lines[cursor_line_idx].lstrip())
                    if cursor_indent > with_indent:
                        in_connection_context = True
                        break

            # Check if THIS SPECIFIC cursor variable is closed (not just any "cursor")
            close_pattern = rf'{re.escape(var_name)}\.close\s*\(\)'
            has_cursor_close = re.search(close_pattern, code)

            if not has_cursor_close and not in_connection_context:
                if self.score > 0:
                    self.vulnerabilities.append({
                        "type": "RESOURCE_LEAK",
                        "severity": "MEDIUM",
                        "description": f"Database cursor '{var_name}' not closed - if error occurs, cursor will leak and hold database resources (locks, memory)",
                        "recommendation": "Use context manager or call {var_name}.close()",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Database cursors hold server-side resources including memory and locks",
                                "Unclosed cursors can hold row locks preventing other transactions",
                                "Cursors must be explicitly closed to release resources"
                            ],
                            "why_vulnerable": [
                                f"Cursor '{var_name}' is created but never closed",
                                f"Line {line_num}: {code_snippet}",
                                "ATTACK: Execute function repeatedly or trigger error conditions → Cursors accumulate without cleanup → Database memory usage grows → Row locks held indefinitely → Other queries blocked → Database performance degrades",
                                "IMPACT: Resource leak causing database memory exhaustion, held locks blocking other transactions, degraded database performance, potential deadlocks"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "*.cursor() - Cursor creation",
                                f"{var_name}.close() - Cursor cleanup (not found)",
                                "with *.cursor() - Context manager (not found)",
                                "Cursor inside connection context manager (not found)"
                            ],
                            "evidence": {
                                "found_patterns": [f"{var_name} = *.cursor() without .close()"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
            elif in_connection_context and not has_cursor_close:
                # Cursor is in connection context manager - downgrade to info/note
                # Many DB drivers auto-close cursors when connection closes
                if self.score == 2:
                    self.vulnerabilities.append({
                        "type": "SECURE",
                        "severity": "INFO",
                        "description": f"Cursor '{var_name}' managed by connection context manager (auto-cleanup likely handled)",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "Cursors should be explicitly closed or managed by context",
                                "Connection context managers often auto-close associated cursors",
                                "Best practice: use context manager for both connection and cursor"
                            ],
                            "why_vulnerable": [],
                            "why_not_vulnerable": [
                                f"Cursor '{var_name}' is inside a connection context manager",
                                f"Line {line_num}: {code_snippet}",
                                "When connection context manager exits, most database drivers automatically close associated cursors",
                                "PROTECTION: Connection cleanup triggers cursor cleanup. No resource leak occurs because connection context manager handles cleanup."
                            ],
                            "patterns_checked": [
                                "*.cursor() - Cursor creation",
                                "with *.connect() - Connection context manager (found)",
                                "Cursor indentation inside 'with' block (found)",
                                "Explicit cursor.close() (not required in this case)"
                            ],
                            "evidence": {
                                "found_patterns": ["cursor inside connection context manager"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })

        # Pattern 3: File handles not properly closed
        file_locations = find_pattern_locations(code, r'(\w+)\s*=\s*open\s*\(')
        has_file_close = re.search(r'\.close\s*\(\)', code)
        has_file_context = re.search(r'with\s+open\(', code)

        if file_locations and not has_file_context:
            location = file_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            # Extract file variable name and filename
            var_match = re.search(r'(\w+)\s*=\s*open\s*\(\s*["\']?([^"\')\s,]+)', code_snippet)
            if var_match:
                var_name = var_match.group(1)
                filename = var_match.group(2)
                resource_desc = f"file handle '{var_name}' ({filename})"
            else:
                resource_desc = "file handle"

            if not has_file_close:
                if self.score > 0:
                    self.vulnerabilities.append({
                        "type": "RESOURCE_LEAK",
                        "severity": "MEDIUM",
                        "description": f"File {resource_desc} opened but never closed - will exhaust file descriptors and cause 'too many open files' errors",
                        "recommendation": "Use 'with open(...)' context manager",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "File descriptors are limited system resources (typically 1024 per process)",
                                "Each open() call consumes a file descriptor until file is closed",
                                "Unclosed files cause file descriptor exhaustion"
                            ],
                            "why_vulnerable": [
                                f"File {resource_desc} opened but never closed",
                                f"Line {line_num}: {code_snippet}",
                                "ATTACK: Call function repeatedly (e.g., API endpoint that reads config file) → Each call opens file without closing → File descriptors accumulate → After ~1000 calls, OS limit reached → Application gets 'OSError: Too many open files' → All file operations fail → Application crashes",
                                "IMPACT: File descriptor exhaustion causing application crash, inability to open files/sockets/database connections, complete application failure"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "open(...) - File opened",
                                ".close() - File cleanup (not found)",
                                "with open(...) - Context manager (not found)",
                                "try/finally with .close() (not found)"
                            ],
                            "evidence": {
                                "found_patterns": ["open() without .close()"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 0
            elif has_file_close and not has_try_finally:
                if self.score > 0:
                    self.vulnerabilities.append({
                        "type": "RESOURCE_LEAK",
                        "severity": "LOW",
                        "description": f"File {resource_desc} not guaranteed to close on error - if exception occurs, file descriptor will leak until program exits",
                        "recommendation": "Use 'with open(...)' context manager",
                        "line_number": line_num,
                        "code_snippet": code_snippet,
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                "File cleanup must be guaranteed even when exceptions occur",
                                ".close() in normal code path won't execute if exception is raised",
                                "Use try/finally or context manager for guaranteed cleanup"
                            ],
                            "why_vulnerable": [
                                f"File {resource_desc} has .close() but not in finally block",
                                f"Line {line_num}: {code_snippet}",
                                "ATTACK: Provide input that triggers error during file processing (e.g., invalid format, I/O error) → Exception raised before .close() → File descriptor leaks → Repeated errors accumulate leaked descriptors → Eventually hits OS limit",
                                "IMPACT: File descriptor leak on error conditions. Under error scenarios, descriptors leak until process restart. Long-running processes eventually hit resource limits."
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                "open(...) - File opened",
                                ".close() - Cleanup exists but may not execute",
                                "try/finally - Guaranteed cleanup (not found)",
                                "with open(...) - Automatic cleanup (not found)"
                            ],
                            "evidence": {
                                "found_patterns": [".close() without try/finally"],
                                "line_numbers": [line_num],
                                "code_snippets": [code_snippet]
                            }
                        }
                    })
                    self.score = 1

        # Pattern 4: LDAP connections not closed
        ldap_locations = find_pattern_locations(code, r'(\w+)\s*=\s*ldap\.initialize\s*\(')
        has_ldap_unbind = re.search(r'\.unbind\s*\(\)', code)

        if ldap_locations and not has_ldap_unbind:
            if self.score > 0:
                location = ldap_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                var_match = re.search(r'(\w+)\s*=', code_snippet)
                var_name = var_match.group(1) if var_match else "conn"

                self.vulnerabilities.append({
                    "type": "RESOURCE_LEAK",
                    "severity": "MEDIUM",
                    "description": f"LDAP connection '{var_name}' not closed (.unbind() not called) - if error occurs, connection will remain open and exhaust LDAP server connection pool",
                    "recommendation": "Call conn.unbind() to close LDAP connection",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "LDAP connections to directory servers must be explicitly closed with .unbind()",
                            "LDAP servers have limited connection pools",
                            "Unclosed connections consume LDAP server resources"
                        ],
                        "why_vulnerable": [
                            f"LDAP connection '{var_name}' initialized but .unbind() never called",
                            f"Line {line_num}: {code_snippet}",
                            "ATTACK: Repeatedly trigger LDAP authentication/queries → Each call opens LDAP connection without closing → LDAP server connection pool exhausted → New LDAP requests timeout → Authentication fails → Users cannot log in",
                            "IMPACT: LDAP server connection pool exhaustion, authentication failures, authorization errors, denial of service for user login/directory services"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "ldap.initialize(...) - LDAP connection opened",
                            ".unbind() - LDAP connection cleanup (not found)",
                            "try/finally with .unbind() (not found)"
                        ],
                        "evidence": {
                            "found_patterns": ["ldap.initialize() without .unbind()"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 5: MongoDB connections not closed
        mongo_locations = find_pattern_locations(code, r'(\w+)\s*=\s*MongoClient\s*\(')
        has_mongo_close = re.search(r'client\.close\s*\(\)', code)

        if mongo_locations and not has_mongo_close:
            if self.score > 0:
                location = mongo_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                var_match = re.search(r'(\w+)\s*=', code_snippet)
                var_name = var_match.group(1) if var_match else "client"

                self.vulnerabilities.append({
                    "type": "RESOURCE_LEAK",
                    "severity": "MEDIUM",
                    "description": f"MongoDB connection '{var_name}' not closed - if error occurs, connection will leak and eventually exhaust MongoDB connection pool, causing timeouts",
                    "recommendation": "Call client.close() or use context manager",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "MongoDB connections must be explicitly closed with client.close()",
                            "MongoClient maintains connection pool with finite size",
                            "Leaked connections exhaust pool and cause new requests to timeout"
                        ],
                        "why_vulnerable": [
                            f"MongoDB client '{var_name}' created but client.close() never called",
                            f"Line {line_num}: {code_snippet}",
                            "ATTACK: Repeatedly call function (e.g., API endpoint accessing MongoDB) → Each call creates new MongoClient without closing → Connection pool exhausted → New MongoDB operations timeout with 'connection pool timeout' error → Application cannot access database",
                            "IMPACT: MongoDB connection pool exhaustion, database operation timeouts, application errors, data access failures"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "MongoClient(...) - MongoDB connection created",
                            "client.close() - Connection cleanup (not found)",
                            "with MongoClient(...) - Context manager (not found)"
                        ],
                        "evidence": {
                            "found_patterns": ["MongoClient() without .close()"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 6: Check for secure implementations
        if has_context_manager or has_file_context:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses context managers for automatic resource cleanup",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Context managers (with statement) provide automatic resource cleanup",
                        "Resources are guaranteed to be cleaned up even if exceptions occur",
                        "Best practice for managing connections, files, and other resources"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code uses 'with' statement for resource management",
                        "Context manager automatically calls cleanup (__exit__) even on exceptions",
                        "PROTECTION: Resources are guaranteed to be released. No resource leaks possible because cleanup is automatic and exception-safe."
                    ],
                    "patterns_checked": [
                        "with *.connect() - Database connection context manager",
                        "with open(...) - File context manager",
                        "with cursor() - Cursor context manager",
                        "Manual .close() calls (not needed with context manager)"
                    ],
                    "evidence": {
                        "found_patterns": ["context manager (with statement)"],
                        "line_numbers": [],
                        "code_snippets": []
                    }
                }
            })
            if self.score == 0:
                self.score = 1

        if has_try_finally:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses try/finally for guaranteed resource cleanup",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "try/finally blocks guarantee cleanup code executes",
                        "finally block runs even if exception occurs in try block",
                        "Ensures resources are released regardless of errors"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code uses try/finally pattern for resource cleanup",
                        "Cleanup code in finally block is guaranteed to execute",
                        "PROTECTION: Resources are released even when exceptions occur. No leak possible because finally always executes."
                    ],
                    "patterns_checked": [
                        "try: ... finally: - Exception-safe cleanup pattern",
                        ".close() in finally block - Guaranteed cleanup",
                        ".close() outside finally (vulnerable pattern not found)"
                    ],
                    "evidence": {
                        "found_patterns": ["try/finally block"],
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
        """Analyze JavaScript code for resource leaks."""

        # Pattern 1: Database connections created but never closed
        connection_locations = find_pattern_locations(code, r'(const|let|var)\s+(\w+)\s*=\s*\w+\.createConnection\s*\(')
        has_connection_end = re.search(r'\.end\s*\(\)|\.close\s*\(\)', code)

        if connection_locations and not has_connection_end:
            location = connection_locations[0]
            line_num = location['line_number']
            code_snippet = location['line_content']

            var_match = re.search(r'(?:const|let|var)\s+(\w+)\s*=', code_snippet)
            var_name = var_match.group(1) if var_match else "connection"

            self.vulnerabilities.append({
                "type": "RESOURCE_LEAK",
                "severity": "HIGH",
                "description": f"Database connection '{var_name}' created but never closed - on every request, connection will leak, exhausting database pool and causing connection timeout errors",
                "recommendation": "Call connection.end() or use connection pooling",
                "line_number": line_num,
                "code_snippet": code_snippet,
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "JavaScript database connections must be explicitly closed with .end() or .close()",
                        "createConnection() creates new connection each time, consuming database resources",
                        "Without cleanup, connections accumulate and exhaust database connection pool"
                    ],
                    "why_vulnerable": [
                        f"Database connection '{var_name}' created but never closed",
                        f"Line {line_num}: {code_snippet}",
                        "ATTACK: Send multiple requests to endpoint → Each request creates new connection without closing → Database connection pool exhausted within seconds → New requests timeout with 'ER_CON_COUNT_ERROR: Too many connections' → Application becomes unresponsive",
                        "IMPACT: Rapid resource exhaustion, database connection pool depletion, application downtime, cascading failures"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "createConnection(...) - Creates new connection",
                        ".end() or .close() - Connection cleanup (not found)",
                        "createPool() - Connection pooling (not found)"
                    ],
                    "evidence": {
                        "found_patterns": ["createConnection() without .end()"],
                        "line_numbers": [line_num],
                        "code_snippets": [code_snippet]
                    }
                }
            })
            self.score = 0

        # Pattern 2: No connection pooling (creates connection per request)
        # Check if connection is created inside route handler
        is_in_route = re.search(r'app\.(get|post|put|delete)', code) and re.search(r'createConnection\s*\(', code)

        if is_in_route and connection_locations:
            # Only report if we haven't already reported connection not closed
            if self.score > 0:
                location = connection_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "RESOURCE_LEAK",
                    "severity": "HIGH",
                    "description": "Creates new database connection per request (no connection pooling) - even if closed properly, connection overhead will degrade performance and may exhaust server resources under load",
                    "recommendation": "Use connection pool: createPool() instead of createConnection()",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Creating new connection per request is inefficient and dangerous",
                            "Connection establishment is expensive (TCP handshake, authentication, etc.)",
                            "Under load, creating many connections can exhaust server resources"
                        ],
                        "why_vulnerable": [
                            "Code creates new database connection inside request handler",
                            f"Line {line_num}: {code_snippet}",
                            "ATTACK: Send high volume of concurrent requests → Each creates new connection → Even with proper .end(), connection creation overhead overwhelms database → Connection establishment delays accumulate → Database CPU/memory exhausted → Server becomes unresponsive",
                            "IMPACT: Poor scalability, database resource exhaustion under load, degraded performance, potential denial of service from legitimate traffic spikes"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "createConnection() inside route handler - Creates connection per request",
                            "createPool() - Connection pooling (not found, would be secure)",
                            "Global connection variable - Reused connection (not found)"
                        ],
                        "evidence": {
                            "found_patterns": ["createConnection() per request"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 3: File descriptors not closed
        fs_open_locations = find_pattern_locations(code, r'fs\.open\s*\(')
        has_fs_close = re.search(r'fs\.close\(', code)

        if fs_open_locations and not has_fs_close:
            if self.score > 0:
                location = fs_open_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                self.vulnerabilities.append({
                    "type": "RESOURCE_LEAK",
                    "severity": "MEDIUM",
                    "description": "File descriptor opened but never closed - if error occurs or on repeated calls, will exhaust available file descriptors and cause EMFILE (too many open files) errors",
                    "recommendation": "Call fs.close() or use fs.readFile/writeFile instead",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "File descriptors in Node.js are limited OS resources",
                            "fs.open() consumes file descriptor until fs.close() is called",
                            "Unclosed descriptors accumulate and exhaust system limits"
                        ],
                        "why_vulnerable": [
                            "File opened with fs.open() but fs.close() never called",
                            f"Line {line_num}: {code_snippet}",
                            "ATTACK: Repeatedly trigger file operations → Each call opens file without closing → File descriptors accumulate → After hitting OS limit (typically 1024), get EMFILE error → All file/socket operations fail → Application crashes",
                            "IMPACT: File descriptor exhaustion, inability to open files or create network connections, application crash, complete service failure"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "fs.open(...) - Low-level file opening",
                            "fs.close(...) - File descriptor cleanup (not found)",
                            "fs.readFile/writeFile - High-level APIs that auto-close (not used)",
                            "Streams with proper cleanup (not found)"
                        ],
                        "evidence": {
                            "found_patterns": ["fs.open() without fs.close()"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 4: Stream not properly closed/ended
        stream_locations = find_pattern_locations(code, r'(const|let|var)\s+(\w+)\s*=\s*\w*\.?(createReadStream|createWriteStream)\s*\(')
        has_stream_close = re.search(r'\.close\(|\.end\(', code)

        if stream_locations and not has_stream_close:
            if self.score > 0:
                location = stream_locations[0]
                line_num = location['line_number']
                code_snippet = location['line_content']

                var_match = re.search(r'(?:const|let|var)\s+(\w+)\s*=', code_snippet)
                var_name = var_match.group(1) if var_match else "stream"

                self.vulnerabilities.append({
                    "type": "RESOURCE_LEAK",
                    "severity": "MEDIUM",
                    "description": f"Stream '{var_name}' created but not properly closed - if error occurs, stream will remain open holding file descriptor and memory, eventually causing resource exhaustion",
                    "recommendation": "Call stream.close() or handle stream 'end' event",
                    "line_number": line_num,
                    "code_snippet": code_snippet,
                    "detection_reasoning": {
                        "criteria_for_vulnerability": [
                            "Node.js streams hold file descriptors and memory buffers",
                            "Streams must be properly closed to release resources",
                            "Unclosed streams can hold locks on files and consume memory"
                        ],
                        "why_vulnerable": [
                            f"Stream '{var_name}' created but not properly closed",
                            f"Line {line_num}: {code_snippet}",
                            "ATTACK: Trigger stream creation repeatedly or cause errors during stream processing → Streams remain open without cleanup → File descriptors and memory buffers accumulate → System resources exhausted → Application fails",
                            "IMPACT: Memory leaks, file descriptor exhaustion, held file locks, degraded performance, eventual crash"
                        ],
                        "why_not_vulnerable": [],
                        "patterns_checked": [
                            "createReadStream/createWriteStream - Stream creation",
                            ".close() or .end() - Stream cleanup (not found)",
                            "stream.on('end') or .on('close') handlers (not found)",
                            ".pipe() with automatic cleanup (not found)"
                        ],
                        "evidence": {
                            "found_patterns": ["Stream created without cleanup"],
                            "line_numbers": [line_num],
                            "code_snippets": [code_snippet]
                        }
                    }
                })
                self.score = 0

        # Pattern 5: Check for secure implementations
        if re.search(r'createPool\(', code):
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses connection pooling (resource efficient)",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Connection pooling reuses connections instead of creating new ones",
                        "Pools maintain fixed number of connections, preventing resource exhaustion",
                        "Automatic connection management and cleanup"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code uses createPool() for database connections",
                        "Connection pool manages connection lifecycle automatically",
                        "PROTECTION: Pool reuses connections, limits total connections, handles cleanup automatically. No resource leaks from creating too many connections."
                    ],
                    "patterns_checked": [
                        "createPool() - Connection pooling (found)",
                        "createConnection() per request - Anti-pattern (not found)",
                        "Connection pool configuration and limits"
                    ],
                    "evidence": {
                        "found_patterns": ["createPool()"],
                        "line_numbers": [],
                        "code_snippets": []
                    }
                }
            })
            if self.score == 0:
                self.score = 1

        if re.search(r'\.finally\(', code):
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "Uses .finally() for cleanup",
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Promise .finally() ensures cleanup code runs regardless of success/failure",
                        "Guarantees resource cleanup even when promise rejects",
                        "JavaScript equivalent of try/finally for async operations"
                    ],
                    "why_vulnerable": [],
                    "why_not_vulnerable": [
                        "Code uses .finally() for cleanup in promise chains",
                        "Cleanup code guaranteed to execute even on errors",
                        "PROTECTION: Resources are released regardless of promise outcome. No leaks on error conditions."
                    ],
                    "patterns_checked": [
                        ".finally() - Promise cleanup handler (found)",
                        ".then().catch() without .finally() - May miss cleanup (not found)"
                    ],
                    "evidence": {
                        "found_patterns": [".finally()"],
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


def test_db_connection_not_closed():
    """Test detection of database connection not closed."""
    vulnerable_code = '''
import psycopg2

def get_user(username):
    conn = psycopg2.connect(dbname='test')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    return cursor.fetchone()
'''
    detector = ResourceLeakDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect unclosed connection"
    assert any(v["type"] == "RESOURCE_LEAK" for v in result["vulnerabilities"])


def test_db_connection_closed_no_finally():
    """Test detection of connection closed but not in finally block."""
    vulnerable_code = '''
import psycopg2

def get_user(username):
    conn = psycopg2.connect(dbname='test')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result
'''
    detector = ResourceLeakDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] <= 1, "Should warn about missing finally block"


def test_context_manager_secure():
    """Test recognition of context manager usage."""
    secure_code = '''
import psycopg2

def get_user(username):
    with psycopg2.connect(dbname='test') as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
'''
    detector = ResourceLeakDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize context manager"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


def test_try_finally_secure():
    """Test recognition of try/finally pattern."""
    secure_code = '''
import psycopg2

def get_user(username):
    conn = psycopg2.connect(dbname='test')
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
'''
    detector = ResourceLeakDetector()
    result = detector.analyze(secure_code)
    assert result["score"] >= 1, "Should recognize try/finally"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


def test_file_not_closed():
    """Test detection of file not closed."""
    vulnerable_code = '''
def read_config():
    f = open('config.txt', 'r')
    data = f.read()
    return data
'''
    detector = ResourceLeakDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect unclosed file"


def test_cursor_not_closed():
    """Test detection of cursor not closed."""
    vulnerable_code = '''
def get_data():
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM data")
    results = cursor.fetchall()
    conn.close()
    return results
'''
    detector = ResourceLeakDetector()
    result = detector.analyze(vulnerable_code)
    assert result["score"] == 0, "Should detect unclosed cursor"


def test_javascript_connection_not_closed():
    """Test detection of unclosed JavaScript database connection."""
    vulnerable_code = '''
const mysql = require('mysql');

app.get('/users', (req, res) => {
    const db = mysql.createConnection({
        host: 'localhost',
        user: 'root',
        password: 'password'
    });

    db.query('SELECT * FROM users', (err, results) => {
        res.json(results);
    });
});
'''
    detector = ResourceLeakDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 0, "Should detect unclosed connection"
    assert any("leak" in v["description"].lower() for v in result["vulnerabilities"])


def test_javascript_no_connection_pooling():
    """Test detection of missing connection pooling."""
    vulnerable_code = '''
app.get('/users', (req, res) => {
    const db = mysql.createConnection(config);
    db.query('SELECT * FROM users', (err, results) => {
        db.end();
        res.json(results);
    });
});
'''
    detector = ResourceLeakDetector()
    result = detector.analyze(vulnerable_code, language="javascript")
    assert result["score"] == 0, "Should detect missing connection pooling"


def test_javascript_connection_pool_secure():
    """Test recognition of connection pooling."""
    secure_code = '''
const pool = mysql.createPool(config);

app.get('/users', (req, res) => {
    pool.query('SELECT * FROM users', (err, results) => {
        res.json(results);
    });
});
'''
    detector = ResourceLeakDetector()
    result = detector.analyze(secure_code, language="javascript")
    assert result["score"] >= 1, "Should recognize connection pooling"
    assert any(v["type"] == "SECURE" for v in result["vulnerabilities"])


if __name__ == "__main__":
    test_db_connection_not_closed()
    test_db_connection_closed_no_finally()
    test_context_manager_secure()
    test_try_finally_secure()
    test_file_not_closed()
    test_cursor_not_closed()
    test_javascript_connection_not_closed()
    test_javascript_no_connection_pooling()
    test_javascript_connection_pool_secure()
    print("All resource leak detection tests passed!")
