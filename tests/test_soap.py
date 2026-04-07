"""
Test suite for detecting SOAP/Web Services security vulnerabilities.

This detector checks for:
- XML Signature Wrapping attacks
- Missing WS-Security
- Weak encryption
- XXE vulnerabilities
- SOAP injection
"""
import re
from typing import Dict
import sys
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.code_locator import find_pattern_locations


class SOAPSecurityDetector:
    """Detects SOAP/Web Services security vulnerabilities in code."""

    def __init__(self):
        self.vulnerabilities = []
        self.score = 0

    def analyze(self, code: str, language: str = "python") -> Dict:
        """Analyze code for SOAP vulnerabilities."""
        if language == "python":
            return self._analyze_python(code)
        elif language == "javascript":
            return self._analyze_javascript(code)
        elif language == "java":
            return self._analyze_java(code)
        else:
            return {"score": 2, "vulnerabilities": [{"type": "SECURE", "severity": "INFO", "description": "Unsupported language"}], "max_score": 2}

    def _analyze_python(self, code: str) -> Dict:
        """Analyze Python code for SOAP vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses SOAP
        uses_soap = re.search(r'from\s+zeep|import\s+zeep|from\s+suds|<soap:|wsse:|SOAPAction', code, re.IGNORECASE)

        if not uses_soap:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern 1: Missing WS-Security
        has_wsse = re.search(r'wsse|UsernameToken|Signature|BinarySecurityToken', code)
        if not has_wsse and uses_soap:
            self.vulnerabilities.append({
                "type": "SOAP_MISSING_WS_SECURITY",
                "severity": "MEDIUM",
                "description": "SOAP service without WS-Security - messages not authenticated or signed",
                "line_number": 0,
                "code_snippet": ""
            })
            self.score -= 1

        # Pattern 2: XXE vulnerability
        xxe_vulnerable = re.search(r'etree\.fromstring|etree\.XML|minidom\.parseString', code)
        if xxe_vulnerable:
            has_defusedxml = re.search(r'defusedxml', code)
            if not has_defusedxml:
                locations = find_pattern_locations(code, r'etree\.fromstring|etree\.XML')
                if locations:
                    self.vulnerabilities.append({
                        "type": "SOAP_XXE_VULNERABILITY",
                        "severity": "HIGH",
                        "description": "SOAP XML parsing without defusedxml - vulnerable to XXE attacks",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # Pattern 3: Weak encryption algorithm
        weak_crypto = re.search(r'sha1|SHA-1|des-|DES|rc4|RC4', code)
        if weak_crypto:
            soap_crypto = re.search(r'signature.*method.*sha1|encryption.*des', code, re.IGNORECASE)
            if soap_crypto:
                locations = find_pattern_locations(code, r'sha1|SHA-1|des-')
                if locations:
                    self.vulnerabilities.append({
                        "type": "SOAP_WEAK_ENCRYPTION",
                        "severity": "MEDIUM",
                        "description": "SOAP using weak cryptographic algorithm",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # Pattern 4: SOAP injection (user input in SOAP XML without sanitization)
        soap_injection = re.search(r'<.*>.*\{|<.*>.*%s|<.*>.*\+.*request\.|SOAPAction.*\+', code)
        if soap_injection:
            # Check if there's proper escaping
            has_escaping = re.search(r'escape|sanitize|etree\.CDATA', code)
            if not has_escaping:
                locations = find_pattern_locations(code, r'<.*>.*\{|<.*>.*%s')
                if locations:
                    self.vulnerabilities.append({
                        "type": "SOAP_INJECTION",
                        "severity": "HIGH",
                        "description": "User input inserted into SOAP XML without escaping - SOAP injection vulnerability",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No SOAP vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_javascript(self, code: str) -> Dict:
        """Analyze JavaScript code for SOAP vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses SOAP
        uses_soap = re.search(r'soap|wsdl|<.*:Envelope|SOAPAction', code, re.IGNORECASE)

        if not uses_soap:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern: SOAP injection
        soap_injection = re.search(r'<.*>.*\$\{|<.*>.*\+.*req\.|SOAPAction.*\+', code)
        if soap_injection:
            has_escaping = re.search(r'escapeXml|sanitize|he\.encode', code)
            if not has_escaping:
                locations = find_pattern_locations(code, r'<.*>.*\$\{|<.*>.*\+')
                if locations:
                    self.vulnerabilities.append({
                        "type": "SOAP_INJECTION",
                        "severity": "HIGH",
                        "description": "User input in SOAP XML without escaping",
                        "line_number": locations[0]['line_number'],
                        "code_snippet": locations[0]['line_content']
                    })
                    self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No SOAP vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }

    def _analyze_java(self, code: str) -> Dict:
        """Analyze Java code for SOAP vulnerabilities."""
        self.vulnerabilities = []
        self.score = 2

        # Check if code uses SOAP
        uses_soap = re.search(r'import.*jax\.ws|import.*soap|@WebService|SOAPMessage', code)

        if not uses_soap:
            return {"score": self.score, "vulnerabilities": self.vulnerabilities, "max_score": 2}

        # Pattern: Missing WS-Security
        has_wsse = re.search(r'WSSecurityHandler|UsernameToken|Signature', code)
        if not has_wsse:
            self.vulnerabilities.append({
                "type": "SOAP_MISSING_WS_SECURITY",
                "severity": "MEDIUM",
                "description": "SOAP service without WS-Security",
                "line_number": 0,
                "code_snippet": ""
            })
            self.score -= 1

        # If no vulnerabilities found, mark as secure
        if not self.vulnerabilities:
            self.vulnerabilities.append({
                "type": "SECURE",
                "severity": "INFO",
                "description": "No SOAP vulnerabilities detected"
            })

        return {
            "score": max(0, self.score),
            "vulnerabilities": self.vulnerabilities,
            "max_score": 2
        }
