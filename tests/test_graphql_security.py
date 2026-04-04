#!/usr/bin/env python3
"""
GraphQL Security Detector

Detects security vulnerabilities in GraphQL APIs including:
- Schema introspection enabled in production
- Missing query depth limiting (recursive queries)
- Missing query complexity limiting (resource exhaustion)
- Batching and aliasing abuse
- Field-level authorization bypass
- N+1 query problem
- SQL injection in resolvers
- IDOR in queries
- Mass assignment in mutations
- WebSocket subscription abuse
"""

import re
from typing import Dict, List


class GraphQLSecurityDetector:
    """Detector for GraphQL API security issues."""

    def __init__(self):
        self.vulnerabilities = []

    def analyze(self, code: str, language: str = 'python') -> Dict:
        """Analyze GraphQL API code for security vulnerabilities."""
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

    def _analyze_python(self, code: str):
        """Analyze Python GraphQL code (Graphene, Ariadne, Strawberry)."""
        lines = code.split('\n')

        # Check for introspection enabled
        self._check_introspection(code, lines)

        # Check for missing query depth limiting
        self._check_query_depth_limiting(code, lines)

        # Check for missing complexity limiting
        self._check_complexity_limiting(code, lines)

        # Check for batching attacks
        self._check_batching_attacks(code, lines)

        # Check for field-level authorization
        self._check_field_level_auth(code, lines)

        # Check for N+1 queries
        self._check_n_plus_one_python(code, lines)

        # Check for SQL injection in resolvers
        self._check_sql_injection_python(code, lines)

        # Check for IDOR
        self._check_idor_python(code, lines)

        # Check for mass assignment
        self._check_mass_assignment_python(code, lines)

        # Check for subscription abuse
        self._check_subscription_abuse(code, lines)

    def _analyze_javascript(self, code: str):
        """Analyze JavaScript GraphQL code (Apollo Server, Express-GraphQL)."""
        lines = code.split('\n')

        # Check for introspection enabled
        self._check_introspection(code, lines)

        # Check for missing query depth limiting
        self._check_query_depth_limiting(code, lines)

        # Check for missing complexity limiting
        self._check_complexity_limiting(code, lines)

        # Check for batching attacks
        self._check_batching_attacks(code, lines)

        # Check for field-level authorization
        self._check_field_level_auth(code, lines)

        # Check for N+1 queries
        self._check_n_plus_one_javascript(code, lines)

        # Check for SQL injection in resolvers
        self._check_sql_injection_javascript(code, lines)

        # Check for IDOR
        self._check_idor_javascript(code, lines)

        # Check for mass assignment
        self._check_mass_assignment_javascript(code, lines)

        # Check for subscription abuse
        self._check_subscription_abuse(code, lines)

    def _check_introspection(self, code: str, lines: List[str]):
        """Check if introspection is enabled in production."""
        # Look for introspection explicitly enabled or comments about it
        introspection_patterns = [
            r'introspection["\']?\s*:\s*True',
            r'introspection["\']?\s*:\s*true',
            r'introspectionEnabled\s*:\s*true',
            r'keep\s+introspection\s+enabled',
            r'disable\s+it.*production\s+later',
            r'disable\s+it.*prod\s+later',
        ]

        # Check if introspection is explicitly disabled
        introspection_disabled = re.search(
            r'introspection["\']?\s*:\s*(False|false)|disableIntrospection',
            code,
            re.IGNORECASE
        )

        if introspection_disabled:
            return  # Introspection is properly disabled

        for pattern in introspection_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'INTROSPECTION_ENABLED',
                    'severity': 'MEDIUM',
                    'description': 'GraphQL introspection enabled - exposes full schema to attackers',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Disable introspection in production (introspection: False or disable via middleware).'
                })

    def _check_query_depth_limiting(self, code: str, lines: List[str]):
        """Check for missing query depth limiting."""
        # Look for comments about deep queries or no depth limits
        depth_patterns = [
            r'query\s+.*any\s+depth',
            r'nested.*any\s+depth',
            r'avoid.*depth.*restrict',
            r'don.?t\s+limit.*depth',
            r'no\s+depth\s+limit',
        ]

        # Check if depth limiting is implemented
        has_depth_limiting = re.search(
            r'depthLimit|maxDepth|queryDepth|depth_limit_validator',
            code,
            re.IGNORECASE
        )

        if has_depth_limiting:
            return  # Depth limiting is implemented

        for pattern in depth_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'MISSING_QUERY_DEPTH_LIMITING',
                    'severity': 'HIGH',
                    'description': 'Missing query depth limiting - allows deeply nested queries causing DoS',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Implement query depth limiting (use depth-limit or graphql-depth-limit).'
                })

    def _check_complexity_limiting(self, code: str, lines: List[str]):
        """Check for missing query complexity limiting."""
        # Look for comments about complexity or no limits
        complexity_patterns = [
            r'don.?t\s+limit.*complexity',
            r'no.*complexity.*limit',
            r'avoid.*complexity.*restrict',
            r'as\s+much\s+data\s+as\s+they\s+need',
            r'request\s+as\s+much',
        ]

        # Check if complexity limiting is implemented
        has_complexity_limiting = re.search(
            r'complexityLimit|queryComplexity|complexity_validator|createComplexityLimitRule',
            code,
            re.IGNORECASE
        )

        if has_complexity_limiting:
            return  # Complexity limiting is implemented

        for pattern in complexity_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'MISSING_COMPLEXITY_LIMITING',
                    'severity': 'HIGH',
                    'description': 'Missing query complexity limiting - allows resource exhaustion attacks',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Implement query complexity analysis and limits (use graphql-query-complexity).'
                })

    def _check_batching_attacks(self, code: str, lines: List[str]):
        """Check for batching and aliasing attack vulnerabilities."""
        # Look for array-based queries or comments about bulk operations
        batching_patterns = [
            r'query\s+multiple\s+.*at\s+once',
            r'query.*\[\s*\d+\s*,\s*\d+',
            r'ids\s*[-:=]\s*\[',
            r'bulk\s+operation',
            r'array-based\s+quer',
        ]

        for pattern in batching_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'BATCHING_ATTACK',
                    'severity': 'MEDIUM',
                    'description': 'Allows batching attacks - multiple queries in one request can bypass rate limiting',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Implement query cost analysis and limit batch sizes.'
                })

    def _check_field_level_auth(self, code: str, lines: List[str]):
        """Check for missing field-level authorization."""
        # Look for comments about adding field-level permissions later
        field_auth_patterns = [
            r'add\s+field-level.*later',
            r'add\s+field.*permission.*later',
            r'focus.*resolver.*work',
            r'get.*resolver.*work',
        ]

        # Check if field-level authorization is implemented
        has_field_auth = re.search(
            r'@(check_auth|require_auth|authorized|permission)|resolve.*check.*permission',
            code,
            re.IGNORECASE
        )

        # Look for private field definitions without authorization
        private_field_pattern = r'(email|phone|address|ssn|password|secret)'
        has_private_fields = re.search(private_field_pattern, code, re.IGNORECASE)

        if has_private_fields and not has_field_auth:
            for pattern in field_auth_patterns:
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    self.vulnerabilities.append({
                        'type': 'FIELD_LEVEL_AUTHORIZATION_BYPASS',
                        'severity': 'CRITICAL',
                        'description': 'Missing field-level authorization - private fields exposed without checks',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Implement field-level authorization for sensitive fields (email, phone, etc.).'
                    })

    def _check_n_plus_one_python(self, code: str, lines: List[str]):
        """Check for N+1 query problems in Python resolvers."""
        # Look for database queries inside loops or resolvers without DataLoader
        n_plus_one_patterns = [
            r'def\s+resolve_\w+.*:\s*\n\s+.*\.query\(',
            r'def\s+resolve_\w+.*:\s*\n\s+.*\.get\(',
            r'for\s+\w+\s+in.*:\s*\n\s+.*\.query\(',
        ]

        # Check if DataLoader is used
        has_dataloader = re.search(r'DataLoader|batch', code, re.IGNORECASE)

        if not has_dataloader:
            for pattern in n_plus_one_patterns:
                matches = re.finditer(pattern, code, re.DOTALL)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    self.vulnerabilities.append({
                        'type': 'N_PLUS_ONE_QUERY',
                        'severity': 'MEDIUM',
                        'description': 'N+1 query problem - resolver makes separate DB query for each item',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Use DataLoader pattern to batch and cache database queries.'
                    })

    def _check_n_plus_one_javascript(self, code: str, lines: List[str]):
        """Check for N+1 query problems in JavaScript resolvers."""
        n_plus_one_patterns = [
            r'resolve:\s*\([^)]*\)\s*=>\s*\{[^}]*\.(findOne|findById|query)',
            r'resolve:\s*async\s*\([^)]*\)\s*=>\s*\{[^}]*await.*\.(find|query)',
            r'for.*of.*\{[^}]*await.*\.(find|query)',
        ]

        has_dataloader = re.search(r'DataLoader|new\s+DataLoader', code, re.IGNORECASE)

        if not has_dataloader:
            for pattern in n_plus_one_patterns:
                matches = re.finditer(pattern, code, re.DOTALL)
                for match in matches:
                    line_num = code[:match.start()].count('\n') + 1
                    self.vulnerabilities.append({
                        'type': 'N_PLUS_ONE_QUERY',
                        'severity': 'MEDIUM',
                        'description': 'N+1 query problem - resolver makes separate DB query for each item',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Use DataLoader pattern to batch and cache database queries.'
                    })

    def _check_sql_injection_python(self, code: str, lines: List[str]):
        """Check for SQL injection in Python resolvers."""
        # Look for string formatting in SQL queries within resolvers
        sql_patterns = [
            r'def\s+resolve_.*:.*execute.*[fF]".*SELECT',
            r'def\s+resolve_.*:.*execute.*".*SELECT.*"\s*%',
            r'def\s+resolve_.*:.*execute.*".*SELECT.*"\s*\+',
            r'def\s+resolve_.*:.*execute.*".*SELECT.*"\.format',
            r'raw.*SQL',
        ]

        for pattern in sql_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.DOTALL)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'SQL_INJECTION',
                    'severity': 'CRITICAL',
                    'description': 'SQL injection in GraphQL resolver - dynamic query construction',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Use parameterized queries or ORM methods with proper escaping.'
                })

    def _check_sql_injection_javascript(self, code: str, lines: List[str]):
        """Check for SQL injection in JavaScript resolvers."""
        sql_patterns = [
            r'resolve:.*\.query\s*\(\s*[`]SELECT.*\$\{',
            r'resolve:.*\.query\s*\(\s*"SELECT[^"]*"\s*\+',
            r'raw.*SQL',
        ]

        for pattern in sql_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.DOTALL)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'SQL_INJECTION',
                    'severity': 'CRITICAL',
                    'description': 'SQL injection in GraphQL resolver - dynamic query construction',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Use parameterized queries or ORM methods with proper escaping.'
                })

    def _check_idor_python(self, code: str, lines: List[str]):
        """Check for IDOR in Python GraphQL queries."""
        # Look for direct ID access without authorization
        idor_patterns = [
            r'def\s+resolve_\w+\(self,\s*info,\s*id\):\s*\n\s+return.*\.get\(id',
            r'def\s+resolve_\w+\(self,\s*info,\s*id\):\s*\n\s+return.*\.filter\(id=id',
        ]

        for pattern in idor_patterns:
            matches = re.finditer(pattern, code, re.DOTALL)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                # Check if there's authorization
                match_context = code[match.start():match.end() + 200]
                if not re.search(r'check|verify|authorize|permission|current_user', match_context, re.IGNORECASE):
                    self.vulnerabilities.append({
                        'type': 'IDOR',
                        'severity': 'HIGH',
                        'description': 'IDOR vulnerability - direct object access without authorization',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Verify user has permission to access the requested resource by ID.'
                    })

    def _check_idor_javascript(self, code: str, lines: List[str]):
        """Check for IDOR in JavaScript GraphQL queries."""
        idor_patterns = [
            r'resolve:.*\(\{.*id.*\}\).*=>.*\.(findById|findOne)\(id',
        ]

        for pattern in idor_patterns:
            matches = re.finditer(pattern, code, re.DOTALL)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                match_context = code[match.start():match.end() + 200]
                if not re.search(r'check|verify|authorize|permission|currentUser', match_context, re.IGNORECASE):
                    self.vulnerabilities.append({
                        'type': 'IDOR',
                        'severity': 'HIGH',
                        'description': 'IDOR vulnerability - direct object access without authorization',
                        'line_number': line_num,
                        'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        'recommendation': 'Verify user has permission to access the requested resource by ID.'
                    })

    def _check_mass_assignment_python(self, code: str, lines: List[str]):
        """Check for mass assignment in Python mutations."""
        # Check if field-level authorization is implemented
        def has_field_level_authorization(code: str) -> bool:
            """Check if code has field-level authorization/whitelisting patterns."""
            field_auth_patterns = [
                r'ADMIN_ONLY_FIELDS\s*=',
                r'PROTECTED_FIELDS\s*=',
                r'SAFE_FIELDS\s*=',
                r'SENSITIVE_FIELDS\s*=',
                r'if.*field.*in.*protected',
                r'if.*not.*is_admin.*and.*field',
                r'attempted.*fields.*intersection',
                r'set\([^)]*\)\s*&\s*\w+_FIELDS',  # set intersection for field checking
                r'if.*key\s+not\s+in\s+allowed',
                r'whitelist.*field',
                r'for\s+key.*if.*key\s+in\s+',  # field whitelisting in loop
            ]

            for pattern in field_auth_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    return True
            return False

        has_field_auth = has_field_level_authorization(code)

        # Look for mutations that accept all fields
        mass_assignment_patterns = [
            r'def\s+mutate.*:.*\.update\(\*\*input',
            r'def\s+mutate.*:.*for\s+key,\s*value\s+in\s+input\.items',
            r'accept\s+all.*field',
            r'all.*field.*input',
        ]

        for pattern in mass_assignment_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.DOTALL)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1

                # If field-level authorization is implemented, don't flag as vulnerable
                if has_field_auth:
                    continue

                self.vulnerabilities.append({
                    'type': 'MASS_ASSIGNMENT',
                    'severity': 'HIGH',
                    'description': 'Mass assignment vulnerability - accepts all input fields without filtering',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Explicitly whitelist allowed fields for update (e.g., only email, username).'
                })

    def _check_mass_assignment_javascript(self, code: str, lines: List[str]):
        """Check for mass assignment in JavaScript mutations."""
        mass_assignment_patterns = [
            r'resolve:.*\.update\(.*\{.*\.\.\.input',
            r'resolve:.*Object\.assign',
            r'accept\s+all.*field',
        ]

        for pattern in mass_assignment_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.DOTALL)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                self.vulnerabilities.append({
                    'type': 'MASS_ASSIGNMENT',
                    'severity': 'HIGH',
                    'description': 'Mass assignment vulnerability - accepts all input fields without filtering',
                    'line_number': line_num,
                    'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                    'recommendation': 'Explicitly whitelist allowed fields for update (destructure specific fields).'
                })

    def _check_subscription_abuse(self, code: str, lines: List[str]):
        """Check for WebSocket subscription abuse."""
        # Look for subscriptions without access control
        subscription_patterns = [
            r'Subscription\s*\{',
            r'subscribe\s*:',
            r'def\s+resolve_\w+\s*\(.*\)\s*:\s*\n\s+yield',
        ]

        has_subscription = any(re.search(pattern, code, re.IGNORECASE) for pattern in subscription_patterns)

        if has_subscription:
            # Check for access control
            has_subscription_auth = re.search(
                r'check.*permission|verify.*access|authorize|room.*access',
                code,
                re.IGNORECASE
            )

            if not has_subscription_auth:
                for pattern in subscription_patterns:
                    matches = re.finditer(pattern, code, re.IGNORECASE)
                    for match in matches:
                        line_num = code[:match.start()].count('\n') + 1
                        self.vulnerabilities.append({
                            'type': 'SUBSCRIPTION_DOS',
                            'severity': 'MEDIUM',
                            'description': 'WebSocket subscription lacks access control - allows unlimited subscriptions',
                            'line_number': line_num,
                            'code_snippet': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                            'recommendation': 'Implement subscription authorization and rate limiting.'
                        })
                        break  # Only report once
