#!/usr/bin/env python3
"""
Universal Fallback Security Detector

This detector provides basic security analysis for categories that don't have
specialized detectors yet. It looks for common security anti-patterns across
all languages and categories.
"""
import re
import ast
from typing import Dict, List


class UniversalFallbackDetector:
    """
    Generic detector that catches common security issues across any category.
    Used as fallback when no specialized detector exists for a category.
    """

    def __init__(self):
        self.name = "Universal Fallback Detector"

    def _validate_syntax(self, code: str, language: str) -> tuple[bool, str]:
        """
        Validate code syntax for common languages.
        Returns (is_valid, error_message).

        FALSE NEGATIVE FIX (Iteration 8):
        - Issue: Broken/unparseable code was defaulting to SECURE (score=2)
        - Root Cause: Regex patterns don't catch syntax errors, detector assumes code is valid
        - Solution: Add syntax validation before pattern matching
        - Impact: Prevents false negatives for malformed/incomplete code
        """
        if language == 'python':
            try:
                ast.parse(code)
                return True, ""
            except SyntaxError as e:
                return False, f"Python syntax error at line {e.lineno}: {e.msg}"
            except Exception as e:
                return False, f"Python parsing error: {str(e)}"

        elif language == 'javascript':
            # Basic JavaScript syntax checks
            # Check for obvious syntax errors that regex can catch
            syntax_errors = []

            # Check for malformed strings
            if re.search(r"['\"].*?['\"]_\w+", code):
                syntax_errors.append("Malformed string literal with invalid characters after quote")

            # Check for incomplete statements
            if re.search(r'var\s+\w+\s*;\s*\w+\s*=', code):
                syntax_errors.append("Incomplete or malformed variable declarations")

            # Check for multiple statements on same line without semicolons (common in broken code)
            broken_multiline = re.findall(r'var\s+\w+\s*=.*?;\s*var\s+\w+\s*;.*?var\s+\w+', code)
            if broken_multiline:
                syntax_errors.append("Suspicious multiple incomplete declarations")

            # Check for unclosed brackets/parentheses
            open_braces = code.count('{') - code.count('}')
            open_parens = code.count('(') - code.count(')')
            open_brackets = code.count('[') - code.count(']')

            if abs(open_braces) > 2 or abs(open_parens) > 2 or abs(open_brackets) > 2:
                syntax_errors.append(f"Unbalanced brackets: braces={open_braces}, parens={open_parens}, brackets={open_brackets}")

            if syntax_errors:
                return False, "; ".join(syntax_errors)
            return True, ""

        # For other languages, skip syntax validation
        return True, ""

    def analyze(self, code: str, language: str = 'python') -> Dict:
        """
        Analyze code for common security anti-patterns.
        Returns a security score and list of vulnerabilities found.
        """
        vulnerabilities = []
        score = 2  # Start with perfect score

        # CRITICAL: Validate syntax first (FALSE NEGATIVE FIX - Iteration 8)
        # Broken/unparseable code should NOT default to SECURE
        is_valid, syntax_error = self._validate_syntax(code, language)
        if not is_valid:
            vulnerabilities.append({
                'type': 'CRITICAL',
                'severity': 'CRITICAL',
                'description': f'Code contains syntax errors and cannot be executed - {syntax_error}',
                'line_number': 0,
                'code_snippet': '',
                'detection_reasoning': {
                    'why_critical': [
                        'Code has syntax errors and would not run',
                        'Cannot perform security analysis on broken code',
                        'Unparseable code indicates incomplete or malformed implementation',
                        'ASSUMPTION: Broken code that cannot execute cannot be secure',
                        f'ERROR DETECTED: {syntax_error}'
                    ],
                    'user_message': 'When detectors identify false positives/negatives, they explain which assumptions or reasoning was incorrect. In this case: the detector found code with syntax errors. The assumption is that code which cannot execute cannot be considered secure. If you believe this code IS secure despite syntax errors, please explain why.'
                }
            })
            # CRITICAL vulnerability forces score to 0 (handled below)

        # Check for hardcoded secrets (universal anti-pattern)
        if self._has_hardcoded_secrets(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'HIGH',
                'description': 'Hardcoded credentials or API keys detected',
                'line_number': 0,
                'code_snippet': ''
            })
            score -= 1

        # Check for disabled security features
        if self._has_disabled_security(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'HIGH',
                'description': 'Security features explicitly disabled',
                'line_number': 0,
                'code_snippet': ''
            })
            score -= 1

        # Check for missing authentication/authorization
        if self._has_missing_auth(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'HIGH',
                'description': 'Missing authentication or authorization checks',
                'line_number': 0,
                'code_snippet': ''
            })
            score -= 1

        # Check for unvalidated input
        if self._has_unvalidated_input(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'MEDIUM',
                'description': 'User input accepted without validation',
                'line_number': 0,
                'code_snippet': ''
            })
            if score == 2:
                score = 1  # Partial credit only if still at perfect score

        # Check for insecure network communication
        if self._has_insecure_network(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'MEDIUM',
                'description': 'Insecure network communication (HTTP, no TLS)',
                'line_number': 0,
                'code_snippet': ''
            })
            if score == 2:
                score = 1  # Partial credit only if still at perfect score

        # Check for weak crypto
        if self._has_weak_crypto(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'MEDIUM',
                'description': 'Weak cryptographic algorithms detected',
                'line_number': 0,
                'code_snippet': ''
            })
            if score == 2:
                score = 1  # Partial credit only if still at perfect score

        # Check for SQL injection patterns
        if self._has_sql_injection(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'HIGH',
                'description': 'Potential SQL injection vulnerability',
                'line_number': 0,
                'code_snippet': ''
            })
            score -= 1

        # Check for command injection patterns
        if self._has_command_injection(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'HIGH',
                'description': 'Potential command injection vulnerability',
                'line_number': 0,
                'code_snippet': ''
            })
            score -= 1

        # Check for XSS patterns
        if self._has_xss(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'HIGH',
                'description': 'Potential XSS vulnerability',
                'line_number': 0,
                'code_snippet': ''
            })
            score -= 1

        # Check for insecure deserialization
        if self._has_insecure_deserialization(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'HIGH',
                'description': 'Insecure deserialization detected',
                'line_number': 0,
                'code_snippet': ''
            })
            score -= 1

        # Check for missing error handling
        if self._has_poor_error_handling(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'LOW',
                'description': 'Poor error handling may leak sensitive information',
                'line_number': 0,
                'code_snippet': ''
            })

        # Check for public/exposed sensitive endpoints
        if self._has_exposed_endpoints(code):
            vulnerabilities.append({
                'type': 'INSECURE',
                'severity': 'HIGH',
                'description': 'Sensitive endpoints exposed without authentication',
                'line_number': 0,
                'code_snippet': ''
            })
            score -= 1

        # If no vulnerabilities found, it's secure
        if not vulnerabilities:
            vulnerabilities.append({
                'type': 'SECURE',
                'severity': 'INFO',
                'description': 'No common security anti-patterns detected',
                'line_number': 0,
                'code_snippet': ''
            })

        # Ensure score doesn't go below 0
        score = max(0, score)

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0
        if any(v.get("severity") == "CRITICAL" for v in vulnerabilities):
            score = 0

        return {
            'score': score,
            'max_score': 2,
            'vulnerabilities': vulnerabilities,
            'analysis': f'Universal fallback analysis for category without specialized detector'
        }

    def _has_hardcoded_secrets(self, code: str) -> bool:
        """Check for hardcoded credentials, API keys, passwords."""
        patterns = [
            r'["\']?api[_-]?key["\']?\s*[=:]\s*["\'][a-zA-Z0-9_-]{20,}["\']',
            r'["\']?password["\']?\s*[=:]\s*["\'][^"\']{1,50}["\']',
            r'["\']?secret["\']?\s*[=:]\s*["\'][a-zA-Z0-9_-]{20,}["\']',
            r'["\']?(aws|azure|gcp)_[a-z_]+["\']?\s*[=:]\s*["\'][^"\']+["\']',
            r'Bearer\s+[a-zA-Z0-9_-]{20,}',
            r'token\s*[=:]\s*["\'][a-zA-Z0-9_-]{20,}["\']',
        ]
        code_lower = code.lower()
        return any(re.search(p, code, re.IGNORECASE) for p in patterns)

    def _has_disabled_security(self, code: str) -> bool:
        """Check for explicitly disabled security features."""
        patterns = [
            r'verify\s*=\s*False',
            r'ssl[_-]?verify\s*=\s*False',
            r'check[_-]?certificate\s*=\s*False',
            r'validate[_-]?ssl\s*=\s*False',
            r'insecure[_-]?skip[_-]?verify\s*=\s*true',
            r'disable[_-]?auth',
            r'skip[_-]?auth',
            r'no[_-]?auth\s*=\s*true',
            r'--insecure',
            r'allow[_-]?insecure',
        ]
        return any(re.search(p, code, re.IGNORECASE) for p in patterns)

    def _has_missing_auth(self, code: str) -> bool:
        """Check for missing authentication/authorization."""
        code_lower = code.lower()

        # Look for public/unauthenticated endpoints
        if re.search(r'@\w+\.(route|get|post|put|delete|patch)\([^)]*\)', code):
            # Found route decorator, check if auth is missing
            has_auth_decorator = bool(re.search(r'@(login_required|authenticated|authorize|require_auth)', code, re.IGNORECASE))
            has_auth_check = bool(re.search(r'(check_auth|verify_auth|authenticate|is_authenticated|require.*auth)', code_lower))
            return not (has_auth_decorator or has_auth_check)

        return False

    def _has_unvalidated_input(self, code: str) -> bool:
        """Check for unvalidated user input."""
        # Look for input sources
        has_input = bool(re.search(r'(request\.|params\[|query\[|input\(|gets|scanf|readLine)', code))

        if has_input:
            # Check for validation
            has_validation = bool(re.search(r'(validate|sanitize|escape|clean|strip|filter|check)', code, re.IGNORECASE))
            return not has_validation

        return False

    def _has_insecure_network(self, code: str) -> bool:
        """Check for insecure network communication."""
        patterns = [
            r'http://[^\'"\s]+',  # HTTP URLs
            r'port\s*=\s*80\b',    # Port 80
            r'ssl\s*=\s*False',
            r'use[_-]?ssl\s*=\s*False',
            r'tls\s*=\s*False',
        ]
        return any(re.search(p, code, re.IGNORECASE) for p in patterns)

    def _has_weak_crypto(self, code: str) -> bool:
        """Check for weak cryptographic algorithms."""
        weak_algos = ['md5', 'sha1', 'des', 'rc4']
        return any(re.search(rf'\b{algo}\b', code, re.IGNORECASE) for algo in weak_algos)

    def _has_sql_injection(self, code: str) -> bool:
        """Check for SQL injection patterns."""
        patterns = [
            r'execute\([\'"].*?\+.*?[\'"]\)',  # String concatenation in SQL
            r'query\([\'"].*?%.*?[\'"]\)',      # String formatting in SQL
            r'f[\'"]SELECT.*?\{.*?\}',          # f-strings in SQL
            r'\.format\(.*?\).*?SELECT',        # .format() with SQL
        ]
        return any(re.search(p, code, re.IGNORECASE) for p in patterns)

    def _has_command_injection(self, code: str) -> bool:
        """Check for command injection patterns."""
        patterns = [
            r'(exec|system|shell_exec|eval|popen)\([\'"].*?\+',
            r'(exec|system|shell_exec|eval|popen)\([\'"].*?%',
            r'(exec|system|shell_exec|eval|popen)\(.*?f[\'"]',
            r'Runtime\.getRuntime\(\)\.exec\(',
        ]
        return any(re.search(p, code, re.IGNORECASE) for p in patterns)

    def _has_xss(self, code: str) -> bool:
        """Check for XSS patterns."""
        patterns = [
            r'innerHTML\s*=.*?\+',
            r'document\.write\(',
            r'eval\(',
            r'dangerouslySetInnerHTML',
        ]
        return any(re.search(p, code, re.IGNORECASE) for p in patterns)

    def _has_insecure_deserialization(self, code: str) -> bool:
        """Check for insecure deserialization."""
        patterns = [
            r'pickle\.loads?\(',
            r'yaml\.load\(',  # without safe_load
            r'unserialize\(',
            r'ObjectInputStream',
        ]
        return any(re.search(p, code, re.IGNORECASE) for p in patterns)

    def _has_poor_error_handling(self, code: str) -> bool:
        """Check for poor error handling."""
        # Look for bare except or generic catch blocks
        return bool(re.search(r'except\s*:', code)) or bool(re.search(r'catch\s*\(Exception', code))

    def _has_exposed_endpoints(self, code: str) -> bool:
        """Check for publicly exposed sensitive endpoints."""
        code_lower = code.lower()

        # Check for admin/sensitive endpoints
        sensitive_patterns = [
            r'/admin',
            r'/api/v\d+/users',
            r'/api/v\d+/config',
            r'/metrics',
            r'/debug',
            r'/_health',
        ]

        has_sensitive_endpoint = any(re.search(p, code_lower) for p in sensitive_patterns)

        if has_sensitive_endpoint:
            # Check if authentication is present
            has_auth = bool(re.search(r'(authenticate|authorize|login_required|check_auth)', code_lower))
            return not has_auth

        return False
