#!/usr/bin/env python3
"""
SOAP Security Detector Validation Tests

Test Coverage:
- Python: WS-Security, XXE, weak crypto, SOAP injection (MEDIUM/HIGH)
- JavaScript: SOAP injection (HIGH)
- Java: WS-Security (MEDIUM)
- Secure patterns: defusedxml, escapeXml, WSSecurityHandler (SECURE)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_soap import SOAPSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)

class TestSOAPDetectorValidation(BaseDetectorValidationTest):
    def get_detector(self):
        return SOAPSecurityDetector()

    def get_samples(self):
        return [
            # ============================================================
            # PYTHON - VULNERABLE SAMPLES
            # ============================================================

            DetectorValidationSample(
                name="python_missing_ws_security",
                code="""
from zeep import Client

client = Client('http://example.com/service?wsdl')
result = client.service.GetData('user_input')
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY"],
                expected_score=(1, 2),
                description="SOAP service without WS-Security - missing authentication",
                tags=["python", "ws-security", "medium"]
            ),

            DetectorValidationSample(
                name="python_xxe_vulnerability_fromstring",
                code="""
from zeep import Client
from lxml import etree

soap_response = get_response()
root = etree.fromstring(soap_response)
data = root.find('.//data').text
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY", "SOAP_XXE_VULNERABILITY"],
                expected_score=(0, 2),
                description="XXE vulnerability - using etree.fromstring without defusedxml",
                tags=["python", "xxe", "high"]
            ),

            DetectorValidationSample(
                name="python_xxe_vulnerability_xml",
                code="""
import zeep
from lxml import etree

soap_msg = receive_soap_message()
tree = etree.XML(soap_msg)
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY", "SOAP_XXE_VULNERABILITY"],
                expected_score=(0, 2),
                description="XXE vulnerability - using etree.XML without defusedxml",
                tags=["python", "xxe", "high"]
            ),

            DetectorValidationSample(
                name="python_weak_encryption_sha1",
                code="""
from zeep import Client

# Configure SOAP with weak SHA-1 signature method
signature_method = 'http://www.w3.org/2000/09/xmldsig#sha1'
client = Client('http://example.com?wsdl')
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY", "SOAP_WEAK_ENCRYPTION"],
                expected_score=(0, 2),
                description="Weak encryption - using SHA-1 signature method",
                tags=["python", "weak-crypto", "medium"]
            ),

            DetectorValidationSample(
                name="python_weak_encryption_des",
                code="""
import zeep

# SOAP with DES encryption
encryption_method = 'http://www.w3.org/2001/04/xmlenc#des-cbc'
client = zeep.Client('http://example.com?wsdl')
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY", "SOAP_WEAK_ENCRYPTION"],
                expected_score=(0, 2),
                description="Weak encryption - using DES encryption method",
                tags=["python", "weak-crypto", "medium"]
            ),

            DetectorValidationSample(
                name="python_soap_injection_format",
                code="""
from zeep import Client

def send_soap_request(username):
    soap_body = f'''<soap:Envelope>
        <soap:Body>
            <GetUser>
                <username>{username}</username>
            </GetUser>
        </soap:Body>
    </soap:Envelope>'''
    return send(soap_body)
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY", "SOAP_INJECTION"],
                expected_score=(0, 2),
                description="SOAP injection - user input in XML without escaping (f-string)",
                tags=["python", "soap-injection", "high"]
            ),

            DetectorValidationSample(
                name="python_soap_injection_percent",
                code="""
import zeep

def create_soap_message(user_data):
    xml = "<soap:Body><data>%s</data></soap:Body>" % user_data
    return xml
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY", "SOAP_INJECTION"],
                expected_score=(0, 2),
                description="SOAP injection - user input in XML without escaping (% formatting)",
                tags=["python", "soap-injection", "high"]
            ),

            DetectorValidationSample(
                name="python_soap_injection_request",
                code="""
from zeep import Client

@app.route('/soap')
def handle_soap():
    body = '<soap:Body><user>%s</user></soap:Body>' % request.params['name']
    return send_soap(body)
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY", "SOAP_INJECTION"],
                expected_score=(0, 2),
                description="SOAP injection - request parameter directly in XML",
                tags=["python", "soap-injection", "high"]
            ),

            DetectorValidationSample(
                name="python_combined_vulnerabilities",
                code="""
from zeep import Client
from lxml import etree

def process_soap(user_input):
    # Missing WS-Security
    client = Client('http://api.example.com?wsdl')

    # SOAP injection
    soap_msg = f'<soap:Body><data>{user_input}</data></soap:Body>'

    # XXE vulnerability
    response = client.send(soap_msg)
    tree = etree.fromstring(response)

    return tree
""",
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY", "SOAP_XXE_VULNERABILITY", "SOAP_INJECTION"],
                expected_score=(0, 2),
                description="Multiple vulnerabilities - missing WS-Security, XXE, and SOAP injection",
                tags=["python", "combined", "high"]
            ),

            # ============================================================
            # PYTHON - SECURE SAMPLES
            # ============================================================

            DetectorValidationSample(
                name="python_secure_with_wsse",
                code="""
from zeep import Client
from zeep.wsse.username import UsernameToken
import defusedxml.ElementTree as ET

client = Client('http://example.com?wsdl',
                wsse=UsernameToken('user', 'pass'))
result = client.service.GetData()
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure SOAP - uses WS-Security with UsernameToken and defusedxml",
                tags=["python", "secure", "ws-security"]
            ),

            DetectorValidationSample(
                name="python_secure_defusedxml_parse",
                code="""
from zeep import Client
from zeep.wsse import signature, BinarySecurityToken
import defusedxml.etree as ET

# Secure XML parsing
response = get_soap_response()
tree = ET.parse(response)
root = tree.getroot()
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure XML parsing - uses defusedxml.etree.parse with WS-Security",
                tags=["python", "secure", "xxe-safe"]
            ),

            DetectorValidationSample(
                name="python_secure_with_escaping",
                code="""
from zeep import Client
from zeep.wsse.username import UsernameToken
from xml.sax.saxutils import escape

def send_soap(user_data):
    client = Client('http://api.example.com?wsdl',
                   wsse=UsernameToken('user', 'pass'))

    # Properly escape user input
    safe_data = escape(user_data)
    result = client.service.ProcessData(safe_data)
    return result
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure SOAP - uses escape() for user input and WS-Security",
                tags=["python", "secure", "injection-safe"]
            ),

            # ============================================================
            # JAVASCRIPT - VULNERABLE SAMPLES
            # ============================================================

            DetectorValidationSample(
                name="javascript_soap_injection_template",
                code="""
const soap = require('soap');

app.post('/soap-request', (req, res) => {
  const username = req.body.username;
  const soapBody = `
    <soap:Envelope>
      <soap:Body>
        <GetUser>
          <username>${username}</username>
        </GetUser>
      </soap:Body>
    </soap:Envelope>
  `;
  sendSoap(soapBody);
});
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_INJECTION"],
                expected_score=(1, 2),
                description="SOAP injection - template literal with user input in XML",
                tags=["javascript", "soap-injection", "high"]
            ),

            DetectorValidationSample(
                name="javascript_soap_injection_concatenation",
                code="""
const soap = require('soap');

function createSoapMessage(data) {
  const xml = '<soap:Body><data>' + req.body.value + '</data></soap:Body>';
  return xml;
}
""",
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_INJECTION"],
                expected_score=(1, 2),
                description="SOAP injection - string concatenation with req.body in XML",
                tags=["javascript", "soap-injection", "high"]
            ),

            # ============================================================
            # JAVASCRIPT - SECURE SAMPLES
            # ============================================================

            DetectorValidationSample(
                name="javascript_secure_escapexml",
                code="""
const soap = require('soap');
const escapeXml = require('escape-xml');

app.post('/soap', (req, res) => {
  const username = escapeXml(req.body.username);
  const soapBody = `
    <soap:Envelope>
      <soap:Body>
        <GetUser>
          <username>${username}</username>
        </GetUser>
      </soap:Body>
    </soap:Envelope>
  `;
  sendSoap(soapBody);
});
""",
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure SOAP - uses escapeXml() for user input",
                tags=["javascript", "secure", "injection-safe"]
            ),

            DetectorValidationSample(
                name="javascript_secure_he_encode",
                code="""
const soap = require('soap');
const he = require('he');

function createSoapRequest(userInput) {
  const safe = he.encode(userInput);
  const xml = '<soap:Body><data>' + safe + '</data></soap:Body>';
  return sendSoapRequest(xml);
}
""",
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure SOAP - uses he.encode() for HTML/XML entity encoding",
                tags=["javascript", "secure", "injection-safe"]
            ),

            # ============================================================
            # JAVA - VULNERABLE SAMPLES
            # ============================================================

            DetectorValidationSample(
                name="java_missing_ws_security",
                code="""
import javax.jws.WebService;
import javax.xml.ws.Endpoint;

@WebService
public class MyService {
    public String getData(String username) {
        return "Data for " + username;
    }

    public static void main(String[] args) {
        Endpoint.publish("http://localhost:8080/service", new MyService());
    }
}
""",
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY"],
                expected_score=(1, 2),
                description="Missing WS-Security - @WebService without security handler",
                tags=["java", "ws-security", "medium"]
            ),

            DetectorValidationSample(
                name="java_soap_message_no_security",
                code="""
import javax.xml.soap.SOAPMessage;
import javax.xml.soap.SOAPBody;
import javax.jws.WebService;

@WebService
public class SecureService {
    public void processMessage(SOAPMessage message) {
        SOAPBody body = message.getSOAPBody();
        String data = body.getTextContent();
        processData(data);
    }
}
""",
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["SOAP_MISSING_WS_SECURITY"],
                expected_score=(1, 2),
                description="SOAP service processing SOAPMessage without WS-Security",
                tags=["java", "ws-security", "medium"]
            ),

            # ============================================================
            # JAVA - SECURE SAMPLES
            # ============================================================

            DetectorValidationSample(
                name="java_secure_ws_security_handler",
                code="""
import javax.jws.WebService;
import javax.xml.ws.Endpoint;
import org.apache.wss4j.dom.handler.WSSecurityHandler;

@WebService
public class SecureService {
    private WSSecurityHandler securityHandler;

    public SecureService() {
        this.securityHandler = new WSSecurityHandler();
    }

    public String getData(String username) {
        return "Secure data";
    }
}
""",
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure SOAP - uses WSSecurityHandler for WS-Security",
                tags=["java", "secure", "ws-security"]
            ),

            DetectorValidationSample(
                name="java_secure_username_token",
                code="""
import javax.jws.WebService;
import org.apache.wss4j.dom.message.token.UsernameToken;
import org.apache.wss4j.dom.message.token.Signature;

@WebService
public class AuthenticatedService {
    private UsernameToken userToken;

    public void authenticate(String username, String password) {
        userToken = new UsernameToken(username, password);
    }

    public String getSecureData() {
        if (userToken != null && userToken.isValid()) {
            return "Secure data";
        }
        throw new SecurityException("Unauthorized");
    }
}
""",
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=["SECURE"],
                expected_score=(2, 2),
                description="Secure SOAP - uses UsernameToken and Signature for authentication",
                tags=["java", "secure", "ws-security"]
            ),

            # ============================================================
            # OUT OF SCOPE - NON-SOAP CODE
            # ============================================================

            DetectorValidationSample(
                name="python_non_soap_code",
                code="""
def calculate_sum(a, b):
    return a + b

result = calculate_sum(5, 10)
print(result)
""",
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-SOAP code - should be out of scope",
                tags=["python", "out-of-scope"]
            ),

            DetectorValidationSample(
                name="javascript_non_soap_code",
                code="""
function processData(data) {
    const result = data.map(x => x * 2);
    return result;
}
""",
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-SOAP JavaScript - should be out of scope",
                tags=["javascript", "out-of-scope"]
            ),

            DetectorValidationSample(
                name="java_non_soap_code",
                code="""
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
""",
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Non-SOAP Java - should be out of scope",
                tags=["java", "out-of-scope"]
            ),
        ]

if __name__ == '__main__':
    import unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSOAPDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ All SOAP Security detector validation tests PASSED")
    else:
        print(f"\n❌ {len(result.failures)} SOAP Security detector validation tests FAILED")
        sys.exit(1)
