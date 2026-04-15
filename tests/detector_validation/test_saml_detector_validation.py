#!/usr/bin/env python3
"""
SAML Security Detector Validation Tests

This module validates that the SAMLSecurityDetector correctly identifies
SAML security vulnerabilities and secure SAML implementation patterns.

Test Coverage:
- Python: Signature validation disabled, weak encryption (SHA-1), missing cert validation,
  XXE vulnerabilities, missing replay protection
- JavaScript: validateSignature: false, weak SHA-1 algorithm, cert: null
- Java: setSignatureValidationRequired(false)
- C#: ValidateSignature=false
- Secure patterns: Proper signature validation, SHA-256+, defusedxml, timestamp checks

Vulnerability Types:
- SAML_SIGNATURE_VALIDATION_DISABLED (CRITICAL) - score 0/2
- SAML_WEAK_ENCRYPTION (MEDIUM) - score 1/2
- SAML_MISSING_CERT_VALIDATION (HIGH) - score 1/2
- SAML_XXE_VULNERABILITY (HIGH) - score 1/2
- SAML_MISSING_REPLAY_PROTECTION (MEDIUM) - score 1/2
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_saml import SAMLSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestSAMLDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for SAML Security Detector."""

    def get_detector(self):
        """Return SAMLSecurityDetector instance."""
        return SAMLSecurityDetector()

    def get_samples(self):
        """Return hand-crafted SAML test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="saml_python_signature_disabled_want_assertions",
                code='''
from saml2 import SAML2Config

config = SAML2Config()
# CRITICAL: Signature validation disabled - allows forged SAML responses
config.want_assertions_signed = False
config.want_response_signed = False
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_SIGNATURE_VALIDATION_DISABLED"],
                expected_score=(0, 2),
                description="SAML signature validation disabled via want_assertions_signed=False",
                tags=["python", "signature-disabled", "critical"]
            ),

            DetectorValidationSample(
                name="saml_python_signature_disabled_validate",
                code='''
from saml2.response import AuthnResponse

def process_saml_response(saml_response_xml):
    # CRITICAL: Signature validation explicitly disabled
    response = AuthnResponse(saml_response_xml)
    response.validate_signature = False
    return response.get_identity()
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_SIGNATURE_VALIDATION_DISABLED"],
                expected_score=(0, 2),
                description="SAML signature validation disabled via validate_signature=False",
                tags=["python", "signature-disabled", "critical"]
            ),

            DetectorValidationSample(
                name="saml_python_weak_encryption_sha1",
                code='''
from saml2.config import Config
import saml2

config = Config()
# MEDIUM: Weak SHA-1 signature algorithm - vulnerable to collision attacks
config.xmlsec_binary = '/usr/bin/xmlsec1'
config.signature_method = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
config.digest_method = "sha1"

# Include timestamp validation to avoid replay protection flag
valid_until = config.NotOnOrAfter
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_WEAK_ENCRYPTION"],
                expected_score=(1, 2),
                description="SAML using weak SHA-1 signature algorithm",
                tags=["python", "weak-encryption", "sha1"]
            ),

            DetectorValidationSample(
                name="saml_python_missing_cert_validation",
                code='''
from saml2.client import Saml2Client
from saml2.config import SPConfig

sp_config = SPConfig()
# HIGH: Certificate validation missing - cannot verify IdP identity
sp_config.cert_file = None
sp_config.key_file = '/path/to/private-key.pem'

# Include timestamp validation to avoid replay protection flag
sp_config.NotBefore = "timestamp"

client = Saml2Client(sp_config)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_MISSING_CERT_VALIDATION"],
                expected_score=(1, 2),
                description="SAML missing certificate validation (cert_file=None)",
                tags=["python", "missing-cert", "high"]
            ),

            DetectorValidationSample(
                name="saml_python_xxe_vulnerability",
                code='''
from lxml import etree
from saml2.response import SAMLResponse

def parse_saml_response(xml_string):
    # HIGH: XXE vulnerability - using lxml without defusedxml
    # Attacker can read local files or perform SSRF
    doc = etree.fromstring(xml_string)
    assertion = doc.find('.//saml:Assertion')

    # Include timestamp validation to avoid replay protection flag
    not_before = doc.get('NotBefore')

    return assertion
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_XXE_VULNERABILITY"],
                expected_score=(1, 2),
                description="SAML XXE vulnerability - etree.fromstring without defusedxml",
                tags=["python", "xxe", "high"]
            ),

            DetectorValidationSample(
                name="saml_python_xxe_minidom",
                code='''
from xml.dom import minidom
import saml2

def validate_saml_assertion(saml_xml):
    # HIGH: XXE vulnerability using minidom.parseString
    dom = minidom.parseString(saml_xml)
    assertion = dom.getElementsByTagName('Assertion')[0]

    # Include timestamp validation to avoid replay protection flag
    valid_until = assertion.getAttribute('NotOnOrAfter')

    return assertion
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_XXE_VULNERABILITY"],
                expected_score=(1, 2),
                description="SAML XXE vulnerability - minidom.parseString without defusedxml",
                tags=["python", "xxe", "minidom", "high"]
            ),

            DetectorValidationSample(
                name="saml_python_missing_replay_protection",
                code='''
from saml2 import SAML2Config
from saml2.response import AuthnResponse

def process_saml(saml_response_xml):
    # MEDIUM: Missing replay protection - no timestamp validation
    # Attacker can replay old SAML responses
    response = AuthnResponse(saml_response_xml)
    identity = response.get_identity()
    return identity
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_MISSING_REPLAY_PROTECTION"],
                expected_score=(1, 2),
                description="SAML missing replay protection - no NotOnOrAfter/NotBefore checks",
                tags=["python", "replay-attack", "medium"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="saml_python_secure_configuration",
                code='''
from saml2 import SAML2Config
from defusedxml import ElementTree as defused_etree

config = SAML2Config()
# SECURE: Signature validation enabled
config.want_assertions_signed = True
config.want_response_signed = True

# SECURE: Strong SHA-256 algorithm
config.signature_method = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"

# SECURE: Certificate validation enabled
config.cert_file = '/path/to/idp-certificate.pem'

def validate_saml_response(saml_xml):
    # SECURE: Using defusedxml to prevent XXE
    doc = defused_etree.fromstring(saml_xml)

    # SECURE: Timestamp validation for replay protection
    not_on_or_after = doc.find('.//NotOnOrAfter')
    not_before = doc.find('.//NotBefore')

    return doc
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SAML implementation with all protections enabled",
                tags=["python", "secure", "complete"]
            ),

            DetectorValidationSample(
                name="saml_python_secure_with_validation",
                code='''
from saml2.client import Saml2Client
from defusedxml.ElementTree import fromstring
import saml2

# SECURE: Proper SAML configuration
config = {
    'want_assertions_signed': True,
    'signature_method': 'sha256',
    'cert_file': '/etc/ssl/certs/idp-cert.pem'
}

def verify_saml(response_xml):
    # SECURE: defusedxml prevents XXE
    tree = fromstring(response_xml)

    # SECURE: Validate timestamps
    valid_until = tree.get('NotOnOrAfter')
    valid_from = tree.get('NotBefore')

    return tree
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SAML with signature validation and timestamp checks",
                tags=["python", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="saml_javascript_signature_disabled",
                code='''
const saml = require('passport-saml');

const samlConfig = {
    entryPoint: 'https://idp.example.com/sso',
    issuer: 'myapp',
    // CRITICAL: Signature validation disabled - authentication bypass
    validateSignature: false,
    cert: fs.readFileSync('./idp-cert.pem', 'utf-8')
};

const strategy = new saml.Strategy(samlConfig, function(profile, done) {
    return done(null, profile);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_SIGNATURE_VALIDATION_DISABLED"],
                expected_score=(0, 2),
                description="SAML signature validation disabled in JavaScript",
                tags=["javascript", "signature-disabled", "critical"]
            ),

            DetectorValidationSample(
                name="saml_javascript_want_assertions_false",
                code='''
const { SAML } = require('saml2-js');

const samlOptions = {
    issuer: 'myservice',
    // CRITICAL: Assertion signature validation disabled
    wantAssertionsSigned: false,
    cert: idpCertificate
};

const sp = new SAML.ServiceProvider(samlOptions);
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_SIGNATURE_VALIDATION_DISABLED"],
                expected_score=(0, 2),
                description="SAML wantAssertionsSigned disabled in JavaScript",
                tags=["javascript", "signature-disabled", "critical"]
            ),

            DetectorValidationSample(
                name="saml_javascript_weak_algorithm_sha1",
                code='''
const saml = require('node-saml');

const config = {
    entryPoint: 'https://sso.example.com',
    // MEDIUM: Weak SHA-1 signature algorithm
    signatureAlgorithm: 'sha1',
    cert: process.env.IDP_CERT
};
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_WEAK_ENCRYPTION"],
                expected_score=(1, 2),
                description="SAML using weak SHA-1 algorithm in JavaScript",
                tags=["javascript", "weak-encryption", "sha1"]
            ),

            DetectorValidationSample(
                name="saml_javascript_missing_cert",
                code='''
const passport = require('passport');
const SamlStrategy = require('passport-saml').Strategy;

const samlStrategy = new SamlStrategy({
    entryPoint: 'https://idp.example.com/saml/sso',
    issuer: 'my-app',
    // HIGH: Certificate validation missing
    cert: null
}, function(profile, done) {
    return done(null, profile);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_MISSING_CERT_VALIDATION"],
                expected_score=(1, 2),
                description="SAML missing certificate validation (cert: null)",
                tags=["javascript", "missing-cert", "high"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="saml_javascript_secure_configuration",
                code='''
const saml = require('passport-saml');
const fs = require('fs');

const samlConfig = {
    entryPoint: 'https://idp.example.com/sso',
    issuer: 'myapp',
    // SECURE: Signature validation enabled
    validateSignature: true,
    wantAssertionsSigned: true,
    // SECURE: Certificate validation
    cert: fs.readFileSync('./idp-cert.pem', 'utf-8'),
    // SECURE: Strong algorithm (SHA-256 is default)
    signatureAlgorithm: 'sha256'
};

const strategy = new saml.Strategy(samlConfig, function(profile, done) {
    return done(null, profile);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SAML configuration in JavaScript",
                tags=["javascript", "secure"]
            ),

            DetectorValidationSample(
                name="saml_javascript_secure_with_sha256",
                code='''
const { SAML } = require('saml2-js');

const samlOptions = {
    issuer: 'myservice',
    // SECURE: Strong SHA-256 algorithm
    signatureAlgorithm: 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256',
    digestAlgorithm: 'sha256',
    // SECURE: Certificate provided
    cert: process.env.IDP_CERTIFICATE
};

const sp = new SAML.ServiceProvider(samlOptions);
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SAML with SHA-256 in JavaScript",
                tags=["javascript", "secure", "sha256"]
            ),

            # ========== VULNERABLE SAMPLES - Java ==========

            DetectorValidationSample(
                name="saml_java_signature_validation_disabled",
                code='''
import org.opensaml.saml.saml2.core.Response;
import org.springframework.security.saml.SAMLAuthenticationProvider;

public class SAMLConfig {
    public void configureSAML() {
        SAMLAuthenticationProvider provider = new SAMLAuthenticationProvider();
        // CRITICAL: Signature validation disabled
        provider.setSignatureValidationRequired(false);
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_SIGNATURE_VALIDATION_DISABLED"],
                expected_score=(0, 2),
                description="SAML signature validation disabled in Java",
                tags=["java", "signature-disabled", "critical"]
            ),

            DetectorValidationSample(
                name="saml_java_want_assertions_false",
                code='''
import org.springframework.security.saml.metadata.MetadataGenerator;

public class SAMLMetadata {
    public MetadataGenerator metadataGenerator() {
        MetadataGenerator generator = new MetadataGenerator();
        // CRITICAL: Assertion signatures not required
        generator.wantAssertionsSigned(false);
        return generator;
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_SIGNATURE_VALIDATION_DISABLED"],
                expected_score=(0, 2),
                description="SAML wantAssertionsSigned disabled in Java",
                tags=["java", "signature-disabled", "critical"]
            ),

            # ========== SECURE SAMPLES - Java ==========

            DetectorValidationSample(
                name="saml_java_secure_configuration",
                code='''
import org.springframework.security.saml.SAMLAuthenticationProvider;
import org.springframework.security.saml.metadata.MetadataGenerator;
import org.opensaml.saml.saml2.core.Assertion;

public class SecureSAMLConfig {
    public SAMLAuthenticationProvider authProvider() {
        SAMLAuthenticationProvider provider = new SAMLAuthenticationProvider();
        // SECURE: Signature validation enabled (default is true)
        return provider;
    }

    public MetadataGenerator metadataGenerator() {
        MetadataGenerator generator = new MetadataGenerator();
        // SECURE: Require assertion signatures
        generator.setWantAssertionsSigned(true);
        return generator;
    }
}
''',
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SAML configuration in Java",
                tags=["java", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - C# ==========

            DetectorValidationSample(
                name="saml_csharp_validate_signature_false",
                code='''
using Sustainsys.Saml2;
using Sustainsys.Saml2.Configuration;

public class SamlConfig
{
    public void Configure()
    {
        var options = new Saml2Options();
        // CRITICAL: Signature validation disabled
        options.SPOptions.ValidateSignature = false;
    }
}
''',
                language="csharp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_SIGNATURE_VALIDATION_DISABLED"],
                expected_score=(0, 2),
                description="SAML signature validation disabled in C#",
                tags=["csharp", "signature-disabled", "critical"]
            ),

            DetectorValidationSample(
                name="saml_csharp_want_assertions_signed_false",
                code='''
using ComponentSpace.Saml2.Configuration;

public class SAMLConfiguration
{
    public void SetupSAML()
    {
        var config = new SAMLConfiguration();
        // CRITICAL: Assertion signature validation disabled
        config.WantAssertionsSigned = false;
    }
}
''',
                language="csharp",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_SIGNATURE_VALIDATION_DISABLED"],
                expected_score=(0, 2),
                description="SAML WantAssertionsSigned disabled in C#",
                tags=["csharp", "signature-disabled", "critical"]
            ),

            # ========== SECURE SAMPLES - C# ==========

            DetectorValidationSample(
                name="saml_csharp_secure_configuration",
                code='''
using Sustainsys.Saml2;
using Sustainsys.Saml2.Configuration;

public class SecureSamlConfig
{
    public void Configure()
    {
        var options = new Saml2Options();
        // SECURE: Signature validation enabled
        options.SPOptions.ValidateSignature = true;
        options.SPOptions.WantAssertionsSigned = true;
    }
}
''',
                language="csharp",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure SAML configuration in C#",
                tags=["csharp", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="saml_python_no_saml_usage",
                code='''
def process_authentication(username, password):
    # SECURE: No SAML usage at all
    import hashlib
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return check_credentials(username, hashed)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="No SAML usage (edge case)",
                tags=["python", "no-saml", "edge-case", "secure"]
            ),

            DetectorValidationSample(
                name="saml_python_multiple_vulnerabilities",
                code='''
from lxml import etree
import saml2

def process_saml(xml_string):
    # CRITICAL: Signature disabled
    config = saml2.Config()
    config.want_assertions_signed = False

    # HIGH: XXE vulnerability
    doc = etree.fromstring(xml_string)

    # MEDIUM: Weak SHA-1
    config.signature_method = "sha1"

    # No timestamp validation
    return doc
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SAML_SIGNATURE_VALIDATION_DISABLED"],
                expected_score=(0, 2),
                description="Multiple SAML vulnerabilities (worst score wins)",
                tags=["python", "multiple-vulnerabilities", "critical"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSAMLDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All SAML detector validation tests PASSED")
        print("The SAMLSecurityDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} SAML detector validation tests FAILED")
        print("The SAMLSecurityDetector has accuracy issues that must be fixed.")
        sys.exit(1)
