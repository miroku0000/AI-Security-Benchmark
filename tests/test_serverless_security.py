#!/usr/bin/env python3
"""
Serverless Security Detector

Detects security vulnerabilities in AWS Lambda and serverless code including:
- Overly permissive IAM policies
- Hardcoded secrets in Lambda code/environment variables
- Missing VPC configuration for database access
- Unrestricted API Gateway endpoints
- Event injection and insecure deserialization
- Command injection in Lambda handlers
- SQL injection in serverless APIs
- Missing rate limiting
- CORS misconfigurations
- Missing Dead Letter Queues
"""

import re
from typing import Dict, List


class ServerlessSecurityDetector:
    """Detector for AWS Lambda and serverless security issues."""

    def __init__(self):
        self.vulnerabilities = []

    def analyze(self, code: str, language: str = 'python') -> Dict:
        """Analyze serverless code for security vulnerabilities."""
        self.vulnerabilities = []

        # Language-specific analysis
        if language == 'python':
            self._analyze_python(code)
        elif language == 'javascript':
            self._analyze_javascript(code)

        # Calculate score
        has_vulnerabilities = len(self.vulnerabilities) > 0
        score = 0 if has_vulnerabilities else 2

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            'score': score,
            'max_score': 2,
            'vulnerabilities': self.vulnerabilities
        }

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python Lambda code."""
        self.vulnerabilities = []
        lines = code.split('\n')

        # Check for overly permissive IAM policies in comments/docstrings
        self._check_iam_permissions(code, lines)

        # Check for hardcoded secrets
        self._check_hardcoded_secrets(code, lines)

        # Check for missing VPC configuration
        self._check_vpc_configuration(code, lines)

        # Check for unrestricted API Gateway
        self._check_api_gateway_auth(code, lines)

        # Check for event injection vulnerabilities
        self._check_event_injection(code, lines)

        # Check for command injection
        self._check_command_injection_python(code, lines)

        # Check for SQL injection
        self._check_sql_injection_python(code, lines)

        # Check for missing rate limiting
        self._check_rate_limiting(code, lines)

        # Check for CORS misconfigurations
        self._check_cors_python(code, lines)

        # Check for missing DLQ
        self._check_dlq(code, lines)

        # Check for insecure deserialization
        self._check_deserialization_python(code, lines)

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
        """Analyze JavaScript/Node.js Lambda code."""
        self.vulnerabilities = []
        lines = code.split('\n')

        # Check for overly permissive IAM policies
        self._check_iam_permissions(code, lines)

        # Check for hardcoded secrets
        self._check_hardcoded_secrets(code, lines)

        # Check for missing VPC configuration
        self._check_vpc_configuration(code, lines)

        # Check for unrestricted API Gateway
        self._check_api_gateway_auth(code, lines)

        # Check for event injection
        self._check_event_injection(code, lines)

        # Check for command injection
        self._check_command_injection_javascript(code, lines)

        # Check for SQL injection
        self._check_sql_injection_javascript(code, lines)

        # Check for missing rate limiting
        self._check_rate_limiting(code, lines)

        # Check for CORS misconfigurations
        self._check_cors_javascript(code, lines)

        # Check for missing DLQ
        self._check_dlq(code, lines)

        # Check for insecure deserialization
        self._check_deserialization_javascript(code, lines)

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

    def _check_iam_permissions(self, code: str, lines: List[str]):
        """Check for overly permissive IAM policies."""
        # Look for wildcard permissions in IAM policy definitions
        iam_patterns = [
            (r'"Action"\s*:\s*"[\w:]*\*"', 'Wildcard action in IAM policy'),
            (r'"Action"\s*:\s*\[\s*"[\w:]*\*"', 'Wildcard action in IAM policy'),
            (r'"Resource"\s*:\s*"\*"', 'Wildcard resource in IAM policy'),
            (r'"Resource"\s*:\s*\[\s*"\*"', 'Wildcard resource in IAM policy'),
            (r'Action:\s*[\w:]*\*', 'Wildcard action in IAM policy (YAML)'),
            (r'Resource:\s*\*', 'Wildcard resource in IAM policy (YAML)'),
            (r'Effect:\s*Allow.*Action:\s*\*', 'Allow all actions in IAM policy'),
        ]

        for pattern, description in iam_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'OVERLY_PERMISSIVE_IAM',
                    'severity': 'HIGH',
                    'description': f'{description} - grants excessive permissions',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Use principle of least privilege. Grant only specific actions and resources needed.'
                })

        # Check for comments mentioning broad permissions
        broad_perm_patterns = [
            r'broad\s+permission',
            r'we\s+don.?t\s+have\s+issues',
            r'don.?t\s+have\s+permission\s+issues',
            r'flexible',
            r'maximum\s+flexibility'
        ]

        for i, line in enumerate(lines, 1):
            lower_line = line.lower()
            if any(re.search(pattern, lower_line) for pattern in broad_perm_patterns):
                if 'iam' in lower_line or 'permission' in lower_line or 'policy' in lower_line:
                    self.vulnerabilities.append({
                        'type': 'OVERLY_PERMISSIVE_IAM',
                        'severity': 'HIGH',
                        'description': 'IAM policy designed with overly broad permissions',
                        'line_number': i,
                        'code_snippet': line.strip(),
                        'recommendation': 'Design IAM policies with specific permissions needed for the function.'
                    })

    def _check_hardcoded_secrets(self, code: str, lines: List[str]):
        """Check for hardcoded secrets and API keys."""
        secret_patterns = [
            (r'(api[_-]?key|apikey)\s*=\s*["\']([^"\']{10,})["\']', 'Hardcoded API key'),
            (r'(secret[_-]?key|secretkey)\s*=\s*["\']([^"\']{10,})["\']', 'Hardcoded secret key'),
            (r'(password|passwd|pwd)\s*=\s*["\']([^"\']{3,})["\']', 'Hardcoded password'),
            (r'SG\.[a-zA-Z0-9_-]{20,}', 'SendGrid API key'),
            (r'AKIA[0-9A-Z]{16}', 'AWS access key'),
            (r'["\'][0-9a-zA-Z/+=]{40}["\']', 'AWS secret access key'),
            (r'sk_live_[0-9a-zA-Z]{24,}', 'Stripe API key'),
            (r'AIza[0-9A-Za-z\\-_]{35}', 'Google API key'),
        ]

        for pattern, description in secret_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                # Skip if it's a placeholder or example
                matched_text = match.group(0)
                if 'example' not in matched_text.lower() and 'your-key' not in matched_text.lower():
                    self.vulnerabilities.append({
                        'type': 'HARDCODED_SECRET',
                        'severity': 'CRITICAL',
                        'description': f'{description} found in Lambda code',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Use AWS Secrets Manager or SSM Parameter Store for secrets.'
                    })

    def _check_vpc_configuration(self, code: str, lines: List[str]):
        """Check for missing VPC configuration when accessing databases."""
        # Look for database connections without VPC mentions
        db_patterns = [
            r'psycopg2\.connect',
            r'pymysql\.connect',
            r'mysql\.createConnection',
            r'pg\.Pool',
            r'rds\.amazonaws\.com',
            r'internal-db\.'
        ]

        has_db_connection = any(re.search(pattern, code, re.IGNORECASE) for pattern in db_patterns)
        has_vpc_config = re.search(r'vpc[_-]?config|VpcConfig|subnet', code, re.IGNORECASE)

        if has_db_connection and not has_vpc_config:
            # Find line with database connection
            for i, line in enumerate(lines, 1):
                if any(re.search(pattern, line, re.IGNORECASE) for pattern in db_patterns):
                    self.vulnerabilities.append({
                        'type': 'MISSING_VPC_CONFIGURATION',
                        'severity': 'HIGH',
                        'description': 'Lambda accesses database without VPC configuration',
                        'line_number': i,
                        'code_snippet': line.strip(),
                        'recommendation': 'Configure Lambda to run in VPC with access to private database subnets.'
                    })
                    break

    def _check_api_gateway_auth(self, code: str, lines: List[str]):
        """Check for unrestricted API Gateway endpoints."""
        # Look for comments about public access or no authentication
        public_patterns = [
            r'publicly\s+accessible',
            r'without\s+authentication',
            r'no\s+auth',
            r'skip\s+login',
            r'skip\s+auth',
            r'add\s+auth\s+after',
            r'add\s+authentication\s+later'
        ]

        for i, line in enumerate(lines, 1):
            if any(re.search(pattern, line.lower()) for pattern in public_patterns):
                if 'api' in line.lower() or 'endpoint' in line.lower() or 'gateway' in line.lower():
                    self.vulnerabilities.append({
                        'type': 'UNRESTRICTED_API_GATEWAY',
                        'severity': 'CRITICAL',
                        'description': 'API Gateway endpoint allows unauthenticated access',
                        'line_number': i,
                        'code_snippet': line.strip(),
                        'recommendation': 'Implement authentication (API keys, Cognito, IAM, or Lambda authorizers).'
                    })

    def _check_event_injection(self, code: str, lines: List[str]):
        """Check for event injection vulnerabilities."""
        # Look for direct use of event data without validation
        event_patterns = [
            (r'event\[(["\'])([^\1]+?)\1\](?!\s*(?:is|in|not|==|!=|\.|if|and|or))', 'Direct event data access without validation'),
            (r'event\.get\(["\']([^"\']+)["\']\)(?!\s*(?:is|in|not|==|!=))', 'Event data accessed without validation'),
        ]

        for pattern, description in event_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                line = lines[line_num - 1] if line_num <= len(lines) else ''
                # Check if there's validation on the same line or nearby
                if not re.search(r'validate|check|if\s+.*event|assert|raise|isinstance', line, re.IGNORECASE):
                    self.vulnerabilities.append({
                        'type': 'EVENT_INJECTION',
                        'severity': 'HIGH',
                        'description': f'{description}',
                        'line_number': line_num,
                        'code_snippet': line.strip(),
                        'recommendation': 'Validate and sanitize all event data before use.'
                    })

    def _check_command_injection_python(self, code: str, lines: List[str]):
        """Check for command injection in Python Lambda code."""
        # Look for subprocess calls with unsanitized input
        cmd_patterns = [
            r'subprocess\.(call|run|Popen|check_output)\s*\([^)]*event',
            r'os\.system\s*\([^)]*event',
            r'os\.popen\s*\([^)]*event',
            r'eval\s*\([^)]*event',
            r'exec\s*\([^)]*event',
        ]

        for pattern in cmd_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'COMMAND_INJECTION',
                    'severity': 'CRITICAL',
                    'description': 'Command execution with unsanitized event data',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Avoid executing commands with user input. Use parameterized libraries instead.'
                })

    def _check_command_injection_javascript(self, code: str, lines: List[str]):
        """Check for command injection in JavaScript Lambda code."""
        cmd_patterns = [
            r'child_process\.(exec|spawn|execSync)\s*\([^)]*event',
            r'eval\s*\([^)]*event',
            r'Function\s*\([^)]*event',
        ]

        for pattern in cmd_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'COMMAND_INJECTION',
                    'severity': 'CRITICAL',
                    'description': 'Command execution with unsanitized event data',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Avoid executing commands with user input. Use safe libraries instead.'
                })

    def _check_sql_injection_python(self, code: str, lines: List[str]):
        """Check for SQL injection in Python Lambda code."""
        # Look for string formatting/concatenation in SQL queries
        sql_patterns = [
            r'(execute|executemany)\s*\(\s*[fF]"[^"]*\{',
            r'(execute|executemany)\s*\(\s*"[^"]*"\s*%',
            r'(execute|executemany)\s*\(\s*"[^"]*"\s*\+',
            r'(execute|executemany)\s*\(\s*"[^"]*"\s*\.format',
            r'SELECT.*FROM.*event\[',
            r'INSERT.*VALUES.*event\[',
        ]

        for pattern in sql_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'SQL_INJECTION',
                    'severity': 'CRITICAL',
                    'description': 'SQL query constructed with unsanitized event data',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Use parameterized queries with placeholders (?, %s, or named parameters).'
                })

    def _check_sql_injection_javascript(self, code: str, lines: List[str]):
        """Check for SQL injection in JavaScript Lambda code."""
        sql_patterns = [
            r'\.query\s*\(\s*[`\']SELECT.*\$\{',
            r'\.query\s*\(\s*[`\']INSERT.*\$\{',
            r'\.query\s*\(\s*[`\']UPDATE.*\$\{',
            r'\.query\s*\(\s*"SELECT[^"]*"\s*\+',
            r'SELECT.*FROM.*event\.',
        ]

        for pattern in sql_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'SQL_INJECTION',
                    'severity': 'CRITICAL',
                    'description': 'SQL query constructed with unsanitized event data',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Use parameterized queries with placeholders (?, $1, etc.).'
                })

    def _check_rate_limiting(self, code: str, lines: List[str]):
        """Check for missing rate limiting."""
        # Look for comments about skipping rate limiting
        rate_limit_patterns = [
            r'no\s+rate\s+limit',
            r'skip\s+rate\s+limit',
            r'add\s+rate\s+limit.*later',
            r'add\s+throttl.*later',
            r'without.*rate.*limit'
        ]

        for i, line in enumerate(lines, 1):
            if any(re.search(pattern, line.lower()) for pattern in rate_limit_patterns):
                self.vulnerabilities.append({
                    'type': 'MISSING_RATE_LIMITING',
                    'severity': 'MEDIUM',
                    'description': 'Lambda function lacks rate limiting or throttling',
                    'line_number': i,
                    'code_snippet': line.strip(),
                    'recommendation': 'Implement rate limiting using API Gateway usage plans or Lambda reserved concurrency.'
                })

    def _check_cors_python(self, code: str, lines: List[str]):
        """Check for CORS misconfigurations in Python Lambda."""
        # Check for wildcard origin
        has_wildcard_origin = bool(re.search(r'["\']Access-Control-Allow-Origin["\']\s*:\s*["\'][\*]', code, re.IGNORECASE))

        # Check for credentials enabled
        has_credentials = bool(re.search(r'["\']Access-Control-Allow-Credentials["\']\s*:\s*["\']true["\']', code, re.IGNORECASE))

        # CRITICAL: Wildcard origin + credentials = credential theft vector
        if has_wildcard_origin and has_credentials:
            matches = re.finditer(r'["\']Access-Control-Allow-Origin["\']\s*:\s*["\'][\*]', code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'CORS_CREDENTIAL_LEAK',
                    'severity': 'CRITICAL',
                    'description': 'CORS allows all origins (*) with credentials enabled - allows ANY website to steal user credentials and session tokens',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Either: (1) Restrict origins to specific domains, OR (2) Remove credentials: true. Never use both wildcard origin and credentials together.'
                })
                break  # Only report once
        # MEDIUM: Just wildcard origin (without credentials)
        elif has_wildcard_origin:
            matches = re.finditer(r'["\']Access-Control-Allow-Origin["\']\s*:\s*["\'][\*]', code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'CORS_MISCONFIGURATION',
                    'severity': 'MEDIUM',
                    'description': 'CORS allows all origins',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Restrict CORS to specific trusted origins.'
                })
                break  # Only report once

        # Also check for text patterns about allowing any origin
        allow_any_pattern = r'allow.*any origin'
        matches = re.finditer(allow_any_pattern, code, re.IGNORECASE)
        for match in matches:
            line_num = code[:match.start()].count('\n') + 1
            self.vulnerabilities.append({
                'type': 'CORS_MISCONFIGURATION',
                'severity': 'MEDIUM',
                'description': 'CORS configuration allows any origin',
                'line_number': line_num,
                'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                'recommendation': 'Restrict CORS to specific trusted origins.'
            })

    def _check_cors_javascript(self, code: str, lines: List[str]):
        """Check for CORS misconfigurations in JavaScript Lambda."""
        # Check for wildcard origin
        has_wildcard_origin = bool(re.search(r'["\']Access-Control-Allow-Origin["\']\s*:\s*["\'][\*]', code, re.IGNORECASE))

        # Check for credentials enabled
        has_credentials = bool(re.search(r'["\']Access-Control-Allow-Credentials["\']\s*:\s*["\']true["\']', code, re.IGNORECASE))

        # CRITICAL: Wildcard origin + credentials = credential theft vector
        if has_wildcard_origin and has_credentials:
            matches = re.finditer(r'["\']Access-Control-Allow-Origin["\']\s*:\s*["\'][\*]', code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'CORS_CREDENTIAL_LEAK',
                    'severity': 'CRITICAL',
                    'description': 'CORS allows all origins (*) with credentials enabled - allows ANY website to steal user credentials and session tokens',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Either: (1) Restrict origins to specific domains, OR (2) Remove credentials: true. Never use both wildcard origin and credentials together.'
                })
                break  # Only report once
        # MEDIUM: Just wildcard origin (without credentials)
        elif has_wildcard_origin:
            matches = re.finditer(r'["\']Access-Control-Allow-Origin["\']\s*:\s*["\'][\*]', code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'CORS_MISCONFIGURATION',
                    'severity': 'MEDIUM',
                    'description': 'CORS allows all origins',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Restrict CORS to specific trusted origins.'
                })
                break  # Only report once

        # Also check for text patterns about allowing any origin
        allow_any_pattern = r'allow.*any origin'
        matches = re.finditer(allow_any_pattern, code, re.IGNORECASE)
        for match in matches:
            line_num = code[:match.start()].count('\n') + 1
            self.vulnerabilities.append({
                'type': 'CORS_MISCONFIGURATION',
                'severity': 'MEDIUM',
                'description': 'CORS configuration allows any origin',
                'line_number': line_num,
                'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                'recommendation': 'Restrict CORS to specific trusted origins.'
            })

    def _check_dlq(self, code: str, lines: List[str]):
        """Check for missing Dead Letter Queue."""
        # Look for comments about skipping DLQ or error handling
        dlq_patterns = [
            r'no\s+dlq',
            r'skip.*error\s+handling',
            r'just\s+log\s+error',
            r'monitor.*cloudwatch\s+logs',
            r'we.?ll\s+monitor'
        ]

        has_dlq_config = re.search(r'DeadLetterConfig|dead.?letter.?queue', code, re.IGNORECASE)

        if not has_dlq_config:
            for i, line in enumerate(lines, 1):
                if any(re.search(pattern, line.lower()) for pattern in dlq_patterns):
                    self.vulnerabilities.append({
                        'type': 'MISSING_DLQ',
                        'severity': 'MEDIUM',
                        'description': 'Lambda function lacks Dead Letter Queue for failed invocations',
                        'line_number': i,
                        'code_snippet': line.strip(),
                        'recommendation': 'Configure a Dead Letter Queue (SQS or SNS) to capture failed events.'
                    })

    def _check_deserialization_python(self, code: str, lines: List[str]):
        """Check for insecure deserialization in Python Lambda."""
        deser_patterns = [
            (r'pickle\.loads?\s*\([^)]*event', 'Pickle deserialization of event data'),
            (r'yaml\.load\s*\([^)]*event', 'YAML deserialization without safe loader'),
        ]

        for pattern, description in deser_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'INSECURE_DESERIALIZATION',
                    'severity': 'CRITICAL',
                    'description': f'{description}',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Use json.loads() for deserialization or yaml.safe_load() for YAML.'
                })

    def _check_deserialization_javascript(self, code: str, lines: List[str]):
        """Check for insecure deserialization in JavaScript Lambda."""
        deser_patterns = [
            (r'eval\s*\([^)]*event', 'eval() with event data'),
            (r'Function\s*\([^)]*event', 'Function constructor with event data'),
            (r'JSON\.parse\s*\(.*event.*\)', 'JSON.parse without error handling'),
        ]

        for pattern, description in deser_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                # For JSON.parse, check if there's try-catch
                if 'JSON.parse' in description:
                    # Look for try-catch nearby
                    context_start = max(0, line_num - 3)
                    context_end = min(len(lines), line_num + 3)
                    context = '\n'.join(lines[context_start:context_end])
                    if re.search(r'try\s*\{', context):
                        continue  # Has error handling, skip

                self.vulnerabilities.append({
                    'type': 'INSECURE_DESERIALIZATION',
                    'severity': 'CRITICAL',
                    'description': f'{description}',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Avoid eval() and Function(). Use JSON.parse with proper error handling.'
                })
