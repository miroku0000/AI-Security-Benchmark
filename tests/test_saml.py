"""
Test suite for detecting SAML (Security Assertion Markup Language) security vulnerabilities.

This detector checks for:
- XML Signature Wrapping attacks
- Missing signature validation
- Weak encryption algorithms
- Missing certificate validation
- Replay attack vulnerabilities
- XXE in SAML processing
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class SAMLSecurityDetector:
    """Detects SAML security vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for SAML vulnerabilities."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        elif language == "java":
            return self._analyze_java(code)
        elif language == "csharp":
            return self._analyze_csharp(code)
        else:
            return {"score": 2, "vulnerabilities": [{"type": "SECURE", "severity": "INFO", "description": "Unsupported language"}], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for SAML vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses SAML
        uses_saml = re.search(r'from\s+saml2|import\s+saml2|OneLogin.*SAML|python-saml|python3-saml', code, re.IGNORECASE)

        if not uses_saml:
            # Check for generic XML signature/SAML terms
            has_saml_terms = re.search(r'SAMLResponse|Assertion|<saml:|SignatureValue|X509Certificate', code)
            if not has_saml_terms:
                return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: Missing or disabled signature validation
        signature_disabled = any([
            re.search(r'want_assertions_signed\s*=\s*False|want_response_signed\s*=\s*False', code),
            re.search(r'validate_signature\s*=\s*False|verify_signature\s*=\s*False', code),
            re.search(r'signature_required\s*=\s*False', code),
        ])

        if signature_disabled:
            locations = find_pattern_locations(code, r'want_assertions_signed\s*=\s*False|want_response_signed\s*=\s*False|validate_signature\s*=\s*False')
            if locations:
                self.vulnerabilities.append({
                    "type": "SAML_SIGNATURE_VALIDATION_DISABLED",
                    "severity": "CRITICAL",
                    "description": "SAML signature validation disabled - attacker can forge SAML responses to bypass authentication",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0  # Auto-fail

        # Pattern 2: Weak encryption (SHA-1 or weaker)
        weak_encryption = re.search(r'sha1|SHA-1|rsa-sha1|DSA-SHA1', code)
        if weak_encryption:
            # Check if it's actually used in SAML context (not just a comment)
            saml_weak_crypto = re.search(r'signature.*method.*sha1|algorithm.*sha1|digest.*sha1', code, re.IGNORECASE)
            if saml_weak_crypto:
                locations = find_pattern_locations(code, r'sha1|SHA-1')
                if locations:
                    self.vulnerabilities.append({
                        "type": "SAML_WEAK_ENCRYPTION",
                        "severity": "MEDIUM",
                        "description": "SAML using weak signature algorithm (SHA-1) - vulnerable to collision attacks, should use SHA-256 or stronger",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # Pattern 3: Missing or improper certificate validation
        missing_cert_validation = any([
            re.search(r'cert_file\s*=\s*None|certificate\s*=\s*None', code),
            re.search(r'validate_cert\s*=\s*False', code),
        ])

        if missing_cert_validation:
            locations = find_pattern_locations(code, r'cert_file\s*=\s*None|validate_cert\s*=\s*False')
            if locations:
                self.vulnerabilities.append({
                    "type": "SAML_MISSING_CERT_VALIDATION",
                    "severity": "HIGH",
                    "description": "SAML certificate validation disabled or missing - cannot verify identity of SAML identity provider",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score -= 1

        # Pattern 4: XXE vulnerability in SAML XML parsing
        xxe_vulnerable = any([
            re.search(r'etree\.fromstring|etree\.XML|minidom\.parseString|xml\.dom\.parse', code),
            re.search(r'parseString|parse\(.*xml', code),
        ])

        if xxe_vulnerable:
            # Check if defusedxml is used
            has_defusedxml = re.search(r'from\s+defusedxml|import\s+defusedxml', code)
            if not has_defusedxml:
                locations = find_pattern_locations(code, r'etree\.fromstring|etree\.XML|minidom\.parseString')
                if locations:
                    self.vulnerabilities.append({
                        "type": "SAML_XXE_VULNERABILITY",
                        "severity": "HIGH",
                        "description": "SAML XML parsing without defusedxml - vulnerable to XXE (XML External Entity) attacks for file disclosure and SSRF",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # Pattern 5: Missing timestamp/replay protection
        missing_replay_protection = not re.search(r'NotOnOrAfter|NotBefore|valid_until|not_before', code)
        if missing_replay_protection and uses_saml:
            self.vulnerabilities.append({
                "type": "SAML_MISSING_REPLAY_PROTECTION",
                "severity": "MEDIUM",
                "description": "SAML response processing without timestamp validation - vulnerable to replay attacks",
                "line_number": 0,
                "code_snippet": ""
            })
            self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No SAML vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for SAML vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses SAML
        uses_saml = re.search(r'passport-saml|saml2-js|node-saml|SAMLResponse', code, re.IGNORECASE)

        if not uses_saml:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: Signature validation disabled
        signature_disabled = re.search(r'validateSignature\s*:\s*false|wantAssertionsSigned\s*:\s*false', code)
        if signature_disabled:
            locations = find_pattern_locations(code, r'validateSignature\s*:\s*false|wantAssertionsSigned\s*:\s*false')
            if locations:
                self.vulnerabilities.append({
                    "type": "SAML_SIGNATURE_VALIDATION_DISABLED",
                    "severity": "CRITICAL",
                    "description": "SAML signature validation disabled - authentication bypass vulnerability",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # Pattern 2: Weak signature algorithm
        weak_algo = re.search(r'signatureAlgorithm.*sha1|digestAlgorithm.*sha1', code, re.IGNORECASE)
        if weak_algo:
            locations = find_pattern_locations(code, r'signatureAlgorithm.*sha1|digestAlgorithm.*sha1')
            if locations:
                self.vulnerabilities.append({
                    "type": "SAML_WEAK_ENCRYPTION",
                    "severity": "MEDIUM",
                    "description": "SAML using weak signature algorithm (SHA-1)",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score -= 1

        # Pattern 3: Certificate validation disabled
        cert_disabled = re.search(r'cert\s*:\s*null|cert\s*:\s*undefined|validateInResponseTo\s*:\s*false', code)
        if cert_disabled:
            locations = find_pattern_locations(code, r'cert\s*:\s*null|validateInResponseTo\s*:\s*false')
            if locations:
                self.vulnerabilities.append({
                    "type": "SAML_MISSING_CERT_VALIDATION",
                    "severity": "HIGH",
                    "description": "SAML certificate validation disabled",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No SAML vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_java(self, code: str) -> Dict:
        """Analyze Java code for SAML vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses SAML
        uses_saml = re.search(r'import.*opensaml|import.*spring\.security\.saml|SAMLCredential|Assertion', code)

        if not uses_saml:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: Signature validation disabled
        signature_disabled = re.search(r'setSignatureValidationRequired\(false\)|wantAssertionsSigned\(false\)', code)
        if signature_disabled:
            locations = find_pattern_locations(code, r'setSignatureValidationRequired\(false\)|wantAssertionsSigned\(false\)')
            if locations:
                self.vulnerabilities.append({
                    "type": "SAML_SIGNATURE_VALIDATION_DISABLED",
                    "severity": "CRITICAL",
                    "description": "SAML signature validation disabled",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No SAML vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_csharp(self, code: str) -> Dict:
        """Analyze C# code for SAML vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses SAML
        uses_saml = re.search(r'using.*Saml|Sustainsys\.Saml2|ComponentSpace\.Saml2', code)

        if not uses_saml:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: Signature validation disabled
        signature_disabled = re.search(r'ValidateSignature\s*=\s*false|WantAssertionsSigned\s*=\s*false', code)
        if signature_disabled:
            locations = find_pattern_locations(code, r'ValidateSignature\s*=\s*false|WantAssertionsSigned\s*=\s*false')
            if locations:
                self.vulnerabilities.append({
                    "type": "SAML_SIGNATURE_VALIDATION_DISABLED",
                    "severity": "CRITICAL",
                    "description": "SAML signature validation disabled",
                    "line_number": locations[0]['line_number'],
                    "code_snippet": locations[0]['line_content']
                })
                self.score = 0

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No SAML vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }
