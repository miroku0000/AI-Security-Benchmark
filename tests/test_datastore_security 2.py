#!/usr/bin/env python3
"""
Data Store Security Detector

Detects security misconfigurations in data stores including:
- Redis: No authentication, protected-mode disabled, dangerous commands, Lua injection, replication security, weak passwords
- Elasticsearch: X-Pack disabled, anonymous access, script injection, index exposure, snapshot misconfig, CORS issues
- Database Configuration: PostgreSQL pg_hba.conf trust auth, MySQL skip-grant-tables, MongoDB no auth, extension execution, file privileges, default credentials
"""

import re
from typing import Dict, List


class DatastoreSecurityDetector:
    """Detector for data store configuration security issues."""

    def __init__(self):
        self.vulnerabilities = []

    def analyze(self, code: str, language: str = 'python') -> Dict:
        """Analyze data store configuration code for security vulnerabilities."""
        self.vulnerabilities = []

        # Language-specific analysis
        if language == 'yaml':
            self._analyze_yaml(code)
        elif language == 'conf':
            self._analyze_conf(code)
        elif language == 'python':
            self._analyze_python(code)
        elif language == 'javascript':
            self._analyze_javascript(code)

        # Calculate score
        has_vulnerabilities = len(self.vulnerabilities) > 0
        score = 0 if has_vulnerabilities else 2

        return {
            'score': score,
            'max_score': 2,
            'vulnerabilities': self.vulnerabilities
        }

    def _analyze_yaml(self, code: str):
        """Analyze YAML configuration files (Redis, Elasticsearch, etc.)."""
        lines = code.split('\n')

        # Redis security checks
        self._check_redis_no_auth(code, lines)
        self._check_redis_protected_mode(code, lines)
        self._check_redis_dangerous_commands(code, lines)
        self._check_redis_lua_injection(code, lines)
        self._check_redis_replication(code, lines)
        self._check_redis_weak_password(code, lines)

        # Elasticsearch security checks
        self._check_elasticsearch_no_auth(code, lines)
        self._check_elasticsearch_script_injection(code, lines)
        self._check_elasticsearch_public_exposure(code, lines)
        self._check_elasticsearch_snapshot_config(code, lines)
        self._check_elasticsearch_cors(code, lines)

    def _analyze_conf(self, code: str):
        """Analyze .conf configuration files (PostgreSQL, MySQL, etc.)."""
        lines = code.split('\n')

        # PostgreSQL pg_hba.conf checks
        self._check_postgresql_trust_auth(code, lines)
        self._check_postgresql_extension_execution(code, lines)

        # MySQL configuration checks
        self._check_mysql_skip_grant_tables(code, lines)
        self._check_mysql_file_privilege(code, lines)

        # General database configuration
        self._check_database_default_credentials(code, lines)

    def _analyze_python(self, code: str):
        """Analyze Python code for data store connection issues."""
        lines = code.split('\n')

        # Redis connection security
        self._check_redis_connection_python(code, lines)

        # Elasticsearch connection security
        self._check_elasticsearch_connection_python(code, lines)

        # Database connection security
        self._check_database_connection_python(code, lines)

    def _analyze_javascript(self, code: str):
        """Analyze JavaScript code for data store connection issues."""
        lines = code.split('\n')

        # Redis connection security
        self._check_redis_connection_javascript(code, lines)

        # Elasticsearch connection security
        self._check_elasticsearch_connection_javascript(code, lines)

    # Redis Security Checks
    def _check_redis_no_auth(self, code: str, lines: List[str]):
        """Check for Redis without authentication."""
        patterns = [
            r'requirepass\s*#',  # Commented out requirepass
            r'#\s*requirepass',  # Commented out requirepass
            r'skip.*requirepass',
            r'no.*password.*redis',
            r'simplified.*no.*auth',
        ]

        # Check if requirepass is properly set
        has_requirepass = re.search(r'requirepass\s+"[^"]+"', code)
        if has_requirepass:
            return  # Authentication is configured

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'REDIS_NO_AUTHENTICATION',
                    'severity': 'CRITICAL',
                    'description': 'Redis configured without authentication (requirepass) - allows unauthorized access',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Set requirepass with a strong password (requirepass "strong_random_password").'
                })

    def _check_redis_protected_mode(self, code: str, lines: List[str]):
        """Check for Redis protected-mode disabled."""
        patterns = [
            r'protected-mode\s+no',
            r'disable.*protected.*mode',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'REDIS_PROTECTED_MODE_DISABLED',
                    'severity': 'HIGH',
                    'description': 'Redis protected-mode disabled - allows external connections without authentication',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Keep protected-mode enabled (protected-mode yes) or configure proper authentication.'
                })

    def _check_redis_dangerous_commands(self, code: str, lines: List[str]):
        """Check for Redis dangerous commands enabled."""
        patterns = [
            r'skip.*rename.*command',
            r'allow.*FLUSHALL',
            r'allow.*CONFIG',
            r'allow.*EVAL',
            r'don.?t.*disable.*dangerous',
        ]

        # Check if dangerous commands are renamed/disabled
        has_command_protection = re.search(r'rename-command\s+(FLUSHALL|CONFIG|EVAL|KEYS)', code)
        if has_command_protection:
            return

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'REDIS_DANGEROUS_COMMANDS',
                    'severity': 'HIGH',
                    'description': 'Redis dangerous commands enabled (FLUSHALL, CONFIG, EVAL) - allows data destruction',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Rename or disable dangerous commands (rename-command FLUSHALL "" or CONFIG "").'
                })

    def _check_redis_lua_injection(self, code: str, lines: List[str]):
        """Check for Redis Lua script injection vulnerabilities."""
        patterns = [
            r'redis\.call\(["\']EVAL["\'],.*\+',
            r'redis\.call\(["\']EVAL["\'],.*%s',
            r'redis\.call\(["\']EVAL["\'],.*f"',
            r'redis\.call\(["\']EVAL["\'],.*\$\{',
            r'EVAL.*concat',
            r'execute.*lua.*user.*input',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'REDIS_LUA_INJECTION',
                    'severity': 'CRITICAL',
                    'description': 'Redis Lua script injection - user input concatenated into EVAL command',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Validate and sanitize user input before using in Lua scripts. Use EVALSHA with predefined scripts.'
                })

    def _check_redis_replication(self, code: str, lines: List[str]):
        """Check for Redis replication without authentication."""
        patterns = [
            r'masterauth\s*#',
            r'#\s*masterauth',
            r'skip.*masterauth',
            r'replication.*no.*auth',
        ]

        # Check if replication is configured
        has_replication = re.search(r'replicaof|slaveof', code, re.IGNORECASE)
        if not has_replication:
            return

        # Check if masterauth is set
        has_masterauth = re.search(r'masterauth\s+"[^"]+"', code)
        if has_masterauth:
            return

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'REDIS_REPLICATION_NO_AUTH',
                    'severity': 'HIGH',
                    'description': 'Redis replication configured without masterauth - insecure master-replica communication',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Set masterauth to match master requirepass (masterauth "master_password").'
                })

    def _check_redis_weak_password(self, code: str, lines: List[str]):
        """Check for Redis weak passwords."""
        weak_password_patterns = [
            r'requirepass\s+"(password|123456|admin|redis|test|dev)"',
            r'requirepass\s+"[^"]{1,7}"',  # Less than 8 characters
        ]

        for pattern in weak_password_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'REDIS_WEAK_PASSWORD',
                    'severity': 'HIGH',
                    'description': 'Redis configured with weak or common password',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Use strong, randomly generated password with at least 20 characters.'
                })

    # Elasticsearch Security Checks
    def _check_elasticsearch_no_auth(self, code: str, lines: List[str]):
        """Check for Elasticsearch without authentication."""
        patterns = [
            r'xpack\.security\.enabled:\s*false',
            r'disable.*security.*feature',
            r'skip.*authentication',
            r'anonymous.*access',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'ELASTICSEARCH_NO_AUTHENTICATION',
                    'severity': 'CRITICAL',
                    'description': 'Elasticsearch security disabled (xpack.security.enabled: false) - no authentication required',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Enable X-Pack security (xpack.security.enabled: true) and configure authentication.'
                })

    def _check_elasticsearch_script_injection(self, code: str, lines: List[str]):
        """Check for Elasticsearch script injection vulnerabilities."""
        patterns = [
            r'inline.*script.*enable',
            r'script\.inline:\s*true',
            r'allow.*inline.*script',
            r'painless.*user.*input',
            r'groovy.*user.*input',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'ELASTICSEARCH_SCRIPT_INJECTION',
                    'severity': 'CRITICAL',
                    'description': 'Elasticsearch inline scripts enabled with user input - allows arbitrary code execution',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Disable inline scripts or use stored scripts with parameterization. Validate all user input.'
                })

    def _check_elasticsearch_public_exposure(self, code: str, lines: List[str]):
        """Check for Elasticsearch exposed to public."""
        patterns = [
            r'network\.host:\s*0\.0\.0\.0',
            r'bind.*all.*interface',
            r'expose.*internet',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'ELASTICSEARCH_PUBLIC_EXPOSURE',
                    'severity': 'CRITICAL',
                    'description': 'Elasticsearch bound to all interfaces (0.0.0.0) - accessible from internet',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Bind to localhost (127.0.0.1) or specific internal IP. Use firewall rules to restrict access.'
                })

    def _check_elasticsearch_snapshot_config(self, code: str, lines: List[str]):
        """Check for insecure Elasticsearch snapshot configurations."""
        patterns = [
            r'path\.repo:.*\/tmp',
            r'snapshot.*world.*readable',
            r'snapshot.*777',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'ELASTICSEARCH_INSECURE_SNAPSHOT',
                    'severity': 'MEDIUM',
                    'description': 'Elasticsearch snapshot repository in insecure location or with overly permissive permissions',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Use secure snapshot location with proper file permissions (700 or 750).'
                })

    def _check_elasticsearch_cors(self, code: str, lines: List[str]):
        """Check for Elasticsearch CORS misconfiguration."""
        patterns = [
            r'http\.cors\.allow-origin:\s*["\']?\*["\']?',
            r'cors.*allow.*all',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'ELASTICSEARCH_CORS_MISCONFIGURATION',
                    'severity': 'HIGH',
                    'description': 'Elasticsearch CORS configured to allow all origins (*) - enables cross-site attacks',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Restrict CORS to specific trusted origins or disable CORS if not needed.'
                })

    # Database Configuration Checks
    def _check_postgresql_trust_auth(self, code: str, lines: List[str]):
        """Check for PostgreSQL trust authentication."""
        patterns = [
            r'host\s+all\s+all\s+\S+\s+trust',
            r'trust.*authentication',
            r'avoid.*password.*prompt',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'POSTGRESQL_TRUST_AUTHENTICATION',
                    'severity': 'CRITICAL',
                    'description': 'PostgreSQL configured with trust authentication - no password required for connections',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Use md5, scram-sha-256, or certificate authentication instead of trust.'
                })

    def _check_postgresql_extension_execution(self, code: str, lines: List[str]):
        """Check for PostgreSQL extension execution vulnerabilities."""
        patterns = [
            r'CREATE EXTENSION.*plpythonu',
            r'CREATE EXTENSION.*plperlu',
            r'untrusted.*language',
            r'allow.*code.*execution',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'POSTGRESQL_UNTRUSTED_EXTENSION',
                    'severity': 'HIGH',
                    'description': 'PostgreSQL untrusted language extension enabled - allows arbitrary code execution',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Avoid untrusted extensions (plpythonu, plperlu). Use trusted variants (plpython3u) if needed.'
                })

    def _check_mysql_skip_grant_tables(self, code: str, lines: List[str]):
        """Check for MySQL skip-grant-tables."""
        patterns = [
            r'skip-grant-tables',
            r'skip.*grant',
            r'disable.*authentication',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'MYSQL_SKIP_GRANT_TABLES',
                    'severity': 'CRITICAL',
                    'description': 'MySQL configured with skip-grant-tables - completely disables authentication',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Remove skip-grant-tables and use proper authentication. Only use for emergency password recovery.'
                })

    def _check_mysql_file_privilege(self, code: str, lines: List[str]):
        """Check for MySQL file privilege abuse."""
        patterns = [
            r'GRANT\s+FILE\s+ON',
            r'local_infile\s*=\s*1',
            r'enable.*LOAD DATA',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'MYSQL_FILE_PRIVILEGE_ABUSE',
                    'severity': 'HIGH',
                    'description': 'MySQL FILE privilege or local_infile enabled - allows reading/writing server files',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Disable local_infile and avoid granting FILE privilege. Use secure_file_priv to restrict file operations.'
                })

    def _check_database_default_credentials(self, code: str, lines: List[str]):
        """Check for default database credentials."""
        patterns = [
            r'(root|admin|postgres).*password["\']?\s*[:=]\s*["\']?(root|admin|password|123456|postgres)',
            r'default.*credential',
            r'keep.*default.*password',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'DATABASE_DEFAULT_CREDENTIALS',
                    'severity': 'CRITICAL',
                    'description': 'Database configured with default or weak credentials',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Change default passwords immediately. Use strong, unique passwords for each database.'
                })

    # Connection Security Checks (Python)
    def _check_redis_connection_python(self, code: str, lines: List[str]):
        """Check for insecure Redis connections in Python."""
        patterns = [
            r'redis\.Redis\([^)]*password=None',
            r'redis\.Redis\([^)]*\)(?!.*password)',
            r'StrictRedis\([^)]*password=None',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.DOTALL)
            for match in matches:
                # Only flag if no password is set within reasonable distance
                match_context = code[match.start():match.end() + 100]
                if 'password=' not in match_context or 'password=None' in match_context:
                    line_num = code[:match.start()].count('\n') + 1
                    self.vulnerabilities.append({
                        'type': 'REDIS_CONNECTION_NO_AUTH',
                        'severity': 'HIGH',
                        'description': 'Redis connection without password authentication',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Add password parameter to Redis connection (password="strong_password").'
                    })

    def _check_elasticsearch_connection_python(self, code: str, lines: List[str]):
        """Check for insecure Elasticsearch connections in Python."""
        patterns = [
            r'Elasticsearch\([^)]*http_auth=None',
            r'Elasticsearch\([^)]*\)(?!.*http_auth)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.DOTALL)
            for match in matches:
                match_context = code[match.start():match.end() + 100]
                if 'http_auth=' not in match_context or 'http_auth=None' in match_context:
                    line_num = code[:match.start()].count('\n') + 1
                    self.vulnerabilities.append({
                        'type': 'ELASTICSEARCH_CONNECTION_NO_AUTH',
                        'severity': 'HIGH',
                        'description': 'Elasticsearch connection without authentication',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Add http_auth parameter with credentials (http_auth=("user", "password")).'
                    })

    def _check_database_connection_python(self, code: str, lines: List[str]):
        """Check for insecure database connections in Python."""
        # Check for MongoDB without authentication
        patterns = [
            r'MongoClient\([^)]*\)(?!.*username)(?!.*authSource)',
            r'MongoClient\([^)]*auth_mechanism=None',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.DOTALL)
            for match in matches:
                match_context = code[match.start():match.end() + 100]
                if 'username=' not in match_context and 'authSource=' not in match_context:
                    line_num = code[:match.start()].count('\n') + 1
                    self.vulnerabilities.append({
                        'type': 'MONGODB_CONNECTION_NO_AUTH',
                        'severity': 'HIGH',
                        'description': 'MongoDB connection without authentication',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Configure MongoDB authentication (username, password, authSource parameters).'
                    })

    # Connection Security Checks (JavaScript)
    def _check_redis_connection_javascript(self, code: str, lines: List[str]):
        """Check for insecure Redis connections in JavaScript."""
        patterns = [
            r'createClient\([^)]*\)(?!.*password)',
            r'createClient\([^)]*password:\s*["\']["\']',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.DOTALL)
            for match in matches:
                match_context = code[match.start():match.end() + 100]
                if 'password:' not in match_context or 'password: ""' in match_context or "password: ''" in match_context:
                    line_num = code[:match.start()].count('\n') + 1
                    self.vulnerabilities.append({
                        'type': 'REDIS_CONNECTION_NO_AUTH',
                        'severity': 'HIGH',
                        'description': 'Redis connection without password authentication',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Add password to Redis connection options.'
                    })

    def _check_elasticsearch_connection_javascript(self, code: str, lines: List[str]):
        """Check for insecure Elasticsearch connections in JavaScript."""
        patterns = [
            r'new\s+Client\([^)]*\)(?!.*auth)',
            r'new\s+elasticsearch\.Client\([^)]*\)(?!.*auth)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, code, re.DOTALL)
            for match in matches:
                match_context = code[match.start():match.end() + 150]
                if 'auth:' not in match_context:
                    line_num = code[:match.start()].count('\n') + 1
                    self.vulnerabilities.append({
                        'type': 'ELASTICSEARCH_CONNECTION_NO_AUTH',
                        'severity': 'HIGH',
                        'description': 'Elasticsearch connection without authentication',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Add auth configuration with username and password.'
                    })
