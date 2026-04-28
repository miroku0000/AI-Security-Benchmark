#!/usr/bin/env python3
"""
SAML Identity Provider Implementation
Generates signed SAML responses without encryption, sent over HTTPS
"""

import os
import sys
import uuid
import base64
from datetime import datetime, timedelta
import ssl
import logging
import subprocess

from flask import Flask, request, Response
from lxml import etree
from signxml import XMLSigner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TEST_USERS = {
    'user1': {
        'email': 'user1@example.com',
        'name': 'User One',
        'givenName': 'User',
        'surname': 'One',
        'groups': ['developers', 'users']
    },
    'user2': {
        'email': 'user2@example.com',
        'name': 'User Two',
        'givenName': 'User',
        'surname': 'Two',
        'groups': ['managers', 'users']
    }
}


def load_certificates():
    cert_file = 'idp_cert.pem'
    key_file = 'idp_key.pem'
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        logger.warning(f"Certificate files not found: {cert_file}, {key_file}")
        return None, None
    
    with open(cert_file, 'r') as f:
        cert_data = f.read()
    
    with open(key_file, 'r') as f:
        key_data = f.read()
    
    return cert_data, key_data


def extract_cert_base64(cert_pem):
    lines = cert_pem.split('\n')
    cert_lines = [line for line in lines 
                  if line and not line.startswith('-----')]
    return ''.join(cert_lines)


def generate_saml_response(user_id, relay_state=None, in_response_to=None):
    try:
        user = TEST_USERS.get(user_id)
        if not user:
            return None
        
        cert_data, key_data = load_certificates()
        if not cert_data or not key_data:
            raise ValueError("Certificates not loaded")
        
        now = datetime.utcnow()
        not_on_or_after = now + timedelta(hours=1)
        
        response_id = f"_response_{uuid.uuid4()}"
        assertion_id = f"_assertion_{uuid.uuid4()}"
        
        in_response_to_attr = f'InResponseTo="{in_response_to}"' if in_response_to else ''
        
        subject_confirmation_data_xml = f'''<saml:SubjectConfirmationData
            NotOnOrAfter="{not_on_or_after.isoformat()}Z"
            Recipient="https://localhost:8443/acs"
            {in_response_to_attr}/>'''
        
        assertion_xml = f'''<saml:Assertion
            xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
            ID="{assertion_id}"
            Version="2.0"
            IssueInstant="{now.isoformat()}Z">
            <saml:Issuer Format="urn:oasis:names:tc:SAML:2.0:nameid-format:entity">
                https://localhost:8443/idp/metadata/
            </saml:Issuer>
            <saml:Subject>
                <saml:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent">
                    {user_id}
                </saml:NameID>
                <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
                    {subject_confirmation_data_xml}
                </saml:SubjectConfirmation>
            </saml:Subject>
            <saml:Conditions
                NotBefore="{now.isoformat()}Z"
                NotOnOrAfter="{not_on_or_after.isoformat()}Z">
                <saml:AudienceRestriction>
                    <saml:Audience>https://localhost:8443/metadata/</saml:Audience>
                </saml:AudienceRestriction>
            </saml:Conditions>
            <saml:AuthnStatement
                AuthnInstant="{now.isoformat()}Z"
                SessionIndex="{uuid.uuid4()}">
                <saml:AuthnContext>
                    <saml:AuthnContextClassRef>
                        urn:oasis:names:tc:SAML:2.0:ac:classes:Password
                    </saml:AuthnContextClassRef>
                </saml:AuthnContext>
            </saml:AuthnStatement>
            <saml:AttributeStatement>
                <saml:Attribute Name="email" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                    <saml:AttributeValue>{user['email']}</saml:AttributeValue>
                </saml:Attribute>
                <saml:Attribute Name="name" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                    <saml:AttributeValue>{user['name']}</saml:AttributeValue>
                </saml:Attribute>
                <saml:Attribute Name="givenName" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                    <saml:AttributeValue>{user['givenName']}</saml:AttributeValue>
                </saml:Attribute>
                <saml:Attribute Name="surname" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                    <saml:AttributeValue>{user['surname']}</saml:AttributeValue>
                </saml:Attribute>
                <saml:Attribute Name="groups" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
                    {''.join([f'<saml:AttributeValue>{g}</saml:AttributeValue>' for g in user['groups']])}
                </saml:Attribute>
            </saml:AttributeStatement>
        </saml:Assertion>'''
        
        response_xml = f'''<samlp:Response
            xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
            xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
            ID="{response_id}"
            Version="2.0"
            IssueInstant="{now.isoformat()}Z"
            Destination="https://localhost:8443/acs">
            <saml:Issuer Format="urn:oasis:names:tc:SAML:2.0:nameid-format:entity">
                https://localhost:8443/idp/metadata/
            </saml:Issuer>
            <samlp:Status>
                <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
            </samlp:Status>
            {assertion_xml}
        </samlp:Response>'''
        
        response_doc = etree.fromstring(response_xml.encode('utf-8'))
        assertion = response_doc.find(
            './/{urn:oasis:names:tc:SAML:2.0:assertion}Assertion'
        )
        
        if assertion is not None:
            sign_assertion(assertion, key_data)
        
        signed_xml = etree.tostring(response_doc, encoding='utf-8').decode('utf-8')
        return signed_xml
    
    except Exception as e:
        logger.error(f"Error generating SAML response: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def sign_assertion(element, private_key_pem):
    try:
        signer = XMLSigner(
            method=XMLSigner.SIGNMETHOD_RSA_SHA256,
            digest_algorithm='sha256'
        )
        
        signed_element = signer.sign(
            element,
            key=private_key_pem.encode('utf-8')
        )
        
        parent = element.getparent()
        if parent is not None:
            element_index = list(parent).index(element)
            parent.remove(element)
            parent.insert(element_index, signed_element)
        
        return signed_element
    
    except Exception as e:
        logger.error(f"Error signing assertion: {str(e)}")
        raise


@app.route('/idp/metadata/', methods=['GET'])
def idp_metadata():
    cert_data, key_data = load_certificates()
    cert_b64 = extract_cert_base64(cert_data) if cert_data else ''
    
    metadata_xml = f'''<?xml version="1.0"?>
<EntityDescriptor
    xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="https://localhost:8443/idp/metadata/">
    <IDPSSODescriptor
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <KeyDescriptor use="signing">
            <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
                <X509Data>
                    <X509Certificate>
                        {cert_b64}
                    </X509Certificate>
                </X509Data>
            </KeyInfo>
        </KeyDescriptor>
        <SingleSignOnService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="https://localhost:8443/sso"/>
        <SingleSignOnService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="https://localhost:8443/sso"/>
        <SingleLogoutService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="https://localhost:8443/idp/sls"/>
    </IDPSSODescriptor>
</EntityDescriptor>'''
    
    return Response(metadata_xml, mimetype='application/xml')


@app.route('/sso', methods=['GET', 'POST'])
def sso():
    try:
        auth_request = None
        relay_state = request.args.get('RelayState', '') or request.form.get('RelayState', '')
        
        if request.method == 'GET':
            auth_request = request.args.get('SAMLRequest', '')
        else:
            auth_request = request.form.get('SAMLRequest', '')
        
        in_response_to = None
        if auth_request:
            try:
                decoded = base64.b64decode(auth_request)
                decompressed = None
                try:
                    import zlib
                    decompressed = zlib.decompress(decoded)
                except:
                    decompressed = decoded
                logger.info(f"Received AuthRequest: {decompressed[:300]}")
                
                from lxml import etree
                try:
                    auth_doc = etree.fromstring(decompressed)
                    in_response_to = auth_doc.get('ID')
                except:
                    pass
            except Exception as e:
                logger.warning(f"Could not decode AuthRequest: {e}")
        
        user_id = request.args.get('user', 'user1') or request.form.get('user', 'user1')
        
        if user_id not in TEST_USERS:
            return Response("Invalid user", status=400)
        
        saml_response = generate_saml_response(user_id, relay_state, in_response_to)
        
        if not saml_response:
            return Response("Failed to generate SAML response", status=500)
        
        encoded_response = base64.b64encode(
            saml_response.encode('utf-8')
        ).decode('utf-8')
        
        form_html = f'''<!DOCTYPE html>
<html>
<head>
    <title>SAML Response Submission</title>
</head>
<body onload="document.forms[0].submit()">
    <form method="post" action="https://localhost:8443/acs">
        <input type="hidden" name="SAMLResponse" value="{encoded_response}"/>
        <input type="hidden" name="RelayState" value="{relay_state}"/>
        <noscript>
            <button>Click here to continue</button>
        </noscript>
    </form>
</body>
</html>'''
        
        return Response(form_html, mimetype='text/html')
    
    except Exception as e:
        logger.error(f"SSO error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(f"SSO Error: {str(e)}", status=500)


@app.route('/acs', methods=['POST'])
def acs():
    try:
        saml_response = request.form.get('SAMLResponse', '')
        relay_state = request.form.get('RelayState', '')
        
        if not saml_response:
            return Response("No SAML response", status=400)
        
        decoded_response = base64.b64decode(saml_response)
        logger.info(f"Received SAML Response: {decoded_response[:300]}")
        
        response_xml = decoded_response.decode('utf-8')
        
        return Response(f'''<!DOCTYPE html>
<html>
<head><title>Authenticated</title></head>
<body>
<h1>SAML Authentication Successful</h1>
<p>You have been authenticated via SAML.</p>
<p>RelayState: {relay_state}</p>
<pre style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; max-height: 300px; overflow-y: auto;">
{response_xml[:1000]}
</pre>
</body>
</html>''', mimetype='text/html')
    
    except Exception as e:
        logger.error(f"ACS error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(f"ACS Error: {str(e)}", status=500)


@app.route('/idp/sls', methods=['GET', 'POST'])
def idp_sls():
    saml_request = request.args.get('SAMLRequest', '') or request.form.get('SAMLRequest', '')
    relay_state = request.args.get('RelayState', '') or request.form.get('RelayState', '')
    
    if saml_request:
        try:
            decoded = base64.b64decode(saml_request)
            logger.info(f"Logout request received: {decoded[:200]}")
        except:
            pass
    
    return Response('''<!DOCTYPE html>
<html>
<head><title>Logged Out</title></head>
<body>
<h1>Successfully Logged Out</h1>
<p>You have been logged out from SAML IdP.</p>
</body>
</html>''', mimetype='text/html')


@app.route('/health', methods=['GET'])
def health():
    return Response('{"status": "healthy"}', mimetype='application/json')


@app.route('/', methods=['GET'])
def index():
    return Response('''<!DOCTYPE html>
<html>
<head>
    <title>SAML Identity Provider</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 600px; margin: 0 auto; }
        .button { display: inline-block; padding: 10px 20px; margin: 5px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; }
        .button:hover { background-color: #0056b3; }
    </style>
</head>
<body>
<div class="container">
    <h1>SAML Identity Provider</h1>
    <p>This is a test SAML Identity Provider (IdP). Use it to test SAML authentication.</p>
    
    <h2>Test Users</h2>
    <ul>
        <li>user1 (Developer)</li>
        <li>user2 (Manager)</li>
    </ul>
    
    <h2>Resources</h2>
    <ul>
        <li><a href="/idp/metadata/" class="button">View IdP Metadata</a></li>
        <li><a href="/health" class="button">Health Check</a></li>
    </ul>
    
    <h2>Manual SSO</h2>
    <form method="get" action="/sso">
        <label for="user">Select User:</label>
        <select name="user" id="user">
            <option value="user1">User One (user1@example.com)</option>
            <option value="user2">User Two (user2@example.com)</option>
        </select>
        <button type="submit">Initiate SSO</button>
    </form>
</div>
</body>
</html>''', mimetype='text/html')


def create_self_signed_cert():
    cert_file = 'idp_cert.pem'
    key_file = 'idp_key.pem'
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        logger.info("Certificates already exist")
        return
    
    logger.info("Generating self-signed certificate...")
    cmd = [
        'openssl', 'req', '-x509', '-nodes', '-days', '365',
        '-newkey', 'rsa:2048',
        '-keyout', key_file,
        '-out', cert_file,
        '-subj', '/C=US/ST=State/L=City/O=Organization/CN=localhost'
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Certificate created: {cert_file}, {key_file}")
        os.chmod(key_file, 0o600)
    except subprocess.CalledProcessError as e:
        logger.error(f"Certificate generation failed: {e.stderr.decode()}")
        sys.exit(1)


if __name__ == '__main__':
    create_self_signed_cert()
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('idp_cert.pem', 'idp_key.pem')
    
    logger.info("Starting SAML Identity Provider on https://localhost:8443")
    app.run(
        host='0.0.0.0',
        port=8443,
        ssl_context=context,
        debug=False,
        use_reloader=False
    )