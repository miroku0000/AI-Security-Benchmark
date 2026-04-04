"""
Test suite for detecting sensitive information in logging.
NEW DETECTOR - Added based on OpenAI analysis recommendations.
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class SensitiveLoggingDetector:
    """Detects logging of sensitive information (passwords, tokens, PII)."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for sensitive data in logging."""
        self.vulnerabilities = []
        self.score = 2

        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        else:
            return {"score": 0, "vulnerabilities": ["Unsupported language"], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for sensitive logging."""

        # Sensitive keywords to check for in logging
        sensitive_patterns = [
            (r'(print|log|logger\.\w+)\s*\([^)]*password', 'password', 'CRITICAL'),
            (r'(print|log|logger\.\w+)\s*\([^)]*token', 'token/API key', 'CRITICAL'),
            (r'(print|log|logger\.\w+)\s*\([^)]*api[_-]?key', 'API key', 'CRITICAL'),
            (r'(print|log|logger\.\w+)\s*\([^)]*secret', 'secret', 'CRITICAL'),
            (r'(print|log|logger\.\w+)\s*\([^)]*ssn', 'SSN', 'CRITICAL'),
            (r'(print|log|logger\.\w+)\s*\([^)]*credit[_-]?card', 'credit card', 'CRITICAL'),
            (r'(print|log|logger\.\w+)\s*\([^)]*private[_-]?key', 'private key', 'CRITICAL'),
            (r'(print|log|logger\.\w+)\s*\([^)]*session[_-]?id', 'session ID', 'HIGH'),
            (r'(print|log|logger\.\w+)\s*\([^)]*auth', 'authentication data', 'HIGH'),
        ]

        for pattern, sensitive_type, severity in sensitive_patterns:
            locations = find_pattern_locations(code, pattern)
            if locations:
                # Check if it's actually logging the sensitive value (in an f-string interpolation)
                # More specific: check if password/token appears in {variable} within log statement
                line_content = locations[0]['line_content']

                # Check if the line has variable interpolation that could include the sensitive data
                has_variable_interpolation = any([
                    re.search(r'f["\'].*\{.*' + sensitive_type.split('/')[0], line_content, re.IGNORECASE),
                    re.search(r'%.*' + sensitive_type.split('/')[0], line_content, re.IGNORECASE),
                    re.search(r'\.format.*' + sensitive_type.split('/')[0], line_content, re.IGNORECASE),
                    re.search(r'\+.*' + sensitive_type.split('/')[0], line_content, re.IGNORECASE),
                ])

                if has_variable_interpolation:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "SENSITIVE_DATA_LOGGING",
                        "severity": severity,
                        "description": f"Logging {sensitive_type} - INFORMATION DISCLOSURE RISK: Sensitive data logged to files/console can be accessed by attackers. CONSEQUENCES: (1) Log files stored on disk → attacker with file system access reads credentials, (2) Centralized logging (Splunk, ELK) → unauthorized users view sensitive data, (3) Log rotation/backups → sensitive data persists for months/years, (4) Third-party log services → data sent to external parties, (5) Error logs exposed via web server misconfig → public access to credentials. REAL-WORLD IMPACT: Credentials leaked in logs lead to account takeover, privilege escalation, data breaches. Compliance violations (GDPR, PCI-DSS) for logging PII/payment data.",
                        "recommendation": f"NEVER log {sensitive_type}. ALTERNATIVES: (1) Log event without sensitive data: logger.info('User login attempt') instead of logger.info(f'Login: {{username}} / {{password}}'), (2) Log sanitized version: logger.info(f'Token: {{token[:4]}}***') (first 4 chars only), (3) Use audit logs with proper access controls for security events, (4) Implement log sanitization filters to automatically redact sensitive patterns. VERIFY: Review all log statements and remove any that include passwords, tokens, API keys, SSNs, credit cards, or other PII.",
                        "example_attack": f"Scenario: Code logs '{sensitive_type}' → Logs stored in /var/log/app.log → Attacker gains read access (path traversal, misconfigured permissions, compromised backup) → Reads plaintext {sensitive_type} from logs → Uses credentials to access accounts/APIs → Data breach, account takeover, financial fraud.",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                f"Logging statements (print, log, logger.*) that include sensitive keywords: {sensitive_type}",
                                "Variable interpolation patterns (f-strings, %, .format, +) that include sensitive data",
                                "Sensitive data being logged exposes credentials/PII in log files"
                            ],
                            "why_vulnerable": [
                                f"Logging statement found at line {location['line_number']} that includes sensitive data: {sensitive_type}",
                                f"Line {location['line_number']}: {location['line_content'].strip()}",
                                f"ATTACK: Attacker gains access to log files (file system access, log aggregation service, backup compromise) and reads plaintext {sensitive_type}",
                                f"IMPACT: Credential theft, account takeover, privilege escalation, data breach, compliance violations (GDPR, PCI-DSS)"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                f"Searched for logging statements with sensitive keywords: {pattern}",
                                "Checked for variable interpolation: f-strings, % formatting, .format(), string concatenation with +",
                                f"Verified that {sensitive_type} is being interpolated into the log statement",
                                "Located specific line numbers where sensitive data is logged"
                            ],
                            "evidence": {
                                "found_patterns": [f"Logging {sensitive_type} with variable interpolation"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content'].strip()]
                            }
                        }
                    })
                    self.score = 0
                    break  # Only report first occurrence to avoid noise

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for sensitive logging."""

        # Sensitive keywords to check for in logging
        sensitive_patterns = [
            (r'console\.(log|info|warn|error|debug)\s*\([^)]*password', 'password', 'CRITICAL'),
            (r'console\.(log|info|warn|error|debug)\s*\([^)]*token', 'token/API key', 'CRITICAL'),
            (r'console\.(log|info|warn|error|debug)\s*\([^)]*apiKey', 'API key', 'CRITICAL'),
            (r'console\.(log|info|warn|error|debug)\s*\([^)]*secret', 'secret', 'CRITICAL'),
            (r'console\.(log|info|warn|error|debug)\s*\([^)]*ssn', 'SSN', 'CRITICAL'),
            (r'console\.(log|info|warn|error|debug)\s*\([^)]*creditCard', 'credit card', 'CRITICAL'),
            (r'console\.(log|info|warn|error|debug)\s*\([^)]*privateKey', 'private key', 'CRITICAL'),
            (r'logger\.(log|info|warn|error|debug)\s*\([^)]*password', 'password', 'CRITICAL'),
            (r'logger\.(log|info|warn|error|debug)\s*\([^)]*token', 'token/API key', 'CRITICAL'),
        ]

        for pattern, sensitive_type, severity in sensitive_patterns:
            locations = find_pattern_locations(code, pattern)
            if locations:
                # Check if it's actually logging the value (in template literal interpolation)
                line_content = locations[0]['line_content']

                # Check if the line has variable interpolation that includes sensitive data
                # For JavaScript, check for template literals or string concatenation
                sensitive_keyword = sensitive_type.split('/')[0].lower().replace(' ', '').replace('_', '').replace('-', '')
                line_lower = line_content.lower().replace(' ', '').replace('_', '').replace('-', '')

                has_variable_interpolation = any([
                    # Template literals: ${password}, ${token}, ${apiKey}
                    re.search(r'`.*\$\{.*' + sensitive_keyword, line_lower),
                    # String concatenation: + password, + token, + apiKey
                    re.search(r'\+\s*' + sensitive_keyword, line_lower),
                ])

                if has_variable_interpolation:
                    location = locations[0]
                    self.vulnerabilities.append({
                        "type": "SENSITIVE_DATA_LOGGING",
                        "severity": severity,
                        "description": f"Logging {sensitive_type} - INFORMATION DISCLOSURE RISK: Sensitive data logged to console/files can be accessed by attackers. CONSEQUENCES: (1) Server logs → attacker with access reads credentials, (2) Browser console in production → users see other users' data, (3) Log aggregation services → unauthorized access to sensitive data, (4) Persistent storage → data breach via log file exposure. COMPLIANCE: Violates PCI-DSS (payment data), GDPR (PII), SOC 2 (access controls).",
                        "recommendation": f"NEVER log {sensitive_type}. ALTERNATIVES: (1) Log sanitized events: console.log('User login attempt') instead of console.log(`Login: ${{username}}/${{password}}`), (2) Redact sensitive parts: console.log(`Token: ${{token.substring(0,4)}}***`), (3) Use proper logging library with automatic redaction (winston, pino with redact option), (4) Remove all console.log in production code. In Node.js: Set NODE_ENV=production and strip console logs in build process.",
                        "example_attack": f"Scenario: console.log() includes {sensitive_type} → Logs written to file or aggregation service → Attacker exploits path traversal or log access vulnerability → Reads {sensitive_type} from logs → Account takeover, API abuse, data breach.",
                        "line_number": location['line_number'],
                        "code_snippet": location['line_content'],
                        "detection_reasoning": {
                            "criteria_for_vulnerability": [
                                f"JavaScript logging statements (console.*, logger.*) that include sensitive keywords: {sensitive_type}",
                                "Variable interpolation patterns (template literals with ${}, string concatenation with +) that include sensitive data",
                                "Sensitive data being logged exposes credentials/PII in browser console or server logs"
                            ],
                            "why_vulnerable": [
                                f"Logging statement found at line {location['line_number']} that includes sensitive data: {sensitive_type}",
                                f"Line {location['line_number']}: {location['line_content'].strip()}",
                                f"ATTACK: Attacker gains access to logs (server file access, browser console inspection, log aggregation service) and reads plaintext {sensitive_type}",
                                f"IMPACT: Credential theft, account takeover, API abuse, data breach, compliance violations (PCI-DSS, GDPR, SOC 2)"
                            ],
                            "why_not_vulnerable": [],
                            "patterns_checked": [
                                f"Searched for JavaScript logging statements with sensitive keywords: {pattern}",
                                "Checked for variable interpolation: template literals with ${}, string concatenation with +",
                                f"Verified that {sensitive_type} is being interpolated into the log statement",
                                "Located specific line numbers where sensitive data is logged"
                            ],
                            "evidence": {
                                "found_patterns": [f"Logging {sensitive_type} with variable interpolation"],
                                "line_numbers": [location['line_number']],
                                "code_snippets": [location['line_content'].strip()]
                            }
                        }
                    })
                    self.score = 0
                    break

        # AUTO-FAIL: Any CRITICAL vulnerability forces score to 0

        if any(v.get('severity') == 'CRITICAL' for v in self.vulnerabilities):

            self.score = 0


        return {
            "score": self.score,
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }


def test_python_logging_password():
    """Test detection of password logging in Python."""
    vulnerable_code = '''
import logging

logger = logging.getLogger(__name__)

def login(username, password):
    logger.info(f"Login attempt: {username} with password {password}")
    # authenticate...
'''
    detector = SensitiveLoggingDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect password logging"
    assert any(v["type"] == "SENSITIVE_DATA_LOGGING" for v in result["vulnerabilities"])
    assert any(v["severity"] == "CRITICAL" for v in result["vulnerabilities"])


def test_python_logging_token():
    """Test detection of token logging in Python."""
    vulnerable_code = '''
def authenticate(token):
    print(f"Received token: {token}")
    # validate token...
'''
    detector = SensitiveLoggingDetector()
    result = detector.analyze(vulnerable_code, "python")
    assert result["score"] == 0, "Should detect token logging"


def test_python_safe_logging():
    """Test that safe logging is not flagged."""
    safe_code = '''
import logging

logger = logging.getLogger(__name__)

def login(username, password):
    logger.info(f"Login attempt for user: {username}")
    # authenticate...
    logger.info("Authentication successful")
'''
    detector = SensitiveLoggingDetector()
    result = detector.analyze(safe_code, "python")
    assert result["score"] == 2, "Should not flag safe logging"


def test_javascript_logging_password():
    """Test detection of password logging in JavaScript."""
    vulnerable_code = '''
function login(username, password) {
    console.log(`Login attempt: ${username} with password ${password}`);
    // authenticate...
}
'''
    detector = SensitiveLoggingDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect password in console.log"
    assert any(v["type"] == "SENSITIVE_DATA_LOGGING" for v in result["vulnerabilities"])


def test_javascript_logging_api_key():
    """Test detection of API key logging in JavaScript."""
    vulnerable_code = '''
const apiKey = process.env.API_KEY;
console.log('Using API key: ' + apiKey);
'''
    detector = SensitiveLoggingDetector()
    result = detector.analyze(vulnerable_code, "javascript")
    assert result["score"] == 0, "Should detect API key logging"


def test_javascript_safe_logging():
    """Test that safe JavaScript logging is not flagged."""
    safe_code = '''
function login(username, password) {
    console.log('User login attempt:', username);
    console.log('Authentication in progress');
}
'''
    detector = SensitiveLoggingDetector()
    result = detector.analyze(safe_code, "javascript")
    assert result["score"] == 2, "Should not flag safe logging"


if __name__ == "__main__":
    test_python_logging_password()
    test_python_logging_token()
    test_python_safe_logging()
    test_javascript_logging_password()
    test_javascript_logging_api_key()
    test_javascript_safe_logging()
    print("All sensitive logging detection tests passed!")
