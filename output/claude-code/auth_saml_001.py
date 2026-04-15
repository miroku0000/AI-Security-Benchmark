from flask import Flask, request, redirect, session, abort
import xml.etree.ElementTree as ET
import base64
import zlib
from datetime import datetime, timezone
from functools import wraps

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-key"

SAML_NAMESPACES = {
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
}

IDP_CONFIG = {
    "sso_url": "https://idp.example.com/sso/saml",
    "entity_id": "https://idp.example.com/metadata",
}

SP_CONFIG = {
    "entity_id": "https://your-app.example.com/saml/metadata",
    "acs_url": "https://your-app.example.com/saml/acs",
}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect("/saml/login")
        return f(*args, **kwargs)
    return decorated


def parse_saml_response(saml_response_b64):
    try:
        xml_bytes = base64.b64decode(saml_response_b64)
    except Exception:
        return None, "Invalid base64 encoding in SAML response"

    try:
        xml_string = xml_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            xml_string = zlib.decompress(xml_bytes, -15).decode("utf-8")
        except Exception:
            return None, "Unable to decode SAML response"

    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError:
        return None, "Invalid XML in SAML response"

    return root, None


def validate_saml_status(root):
    status_code = root.find(".//samlp:Status/samlp:StatusCode", SAML_NAMESPACES)
    if status_code is None:
        return False, "Missing Status element in SAML response"

    status_value = status_code.get("Value", "")
    if status_value != "urn:oasis:names:tc:SAML:2.0:status:Success":
        return False, f"SAML authentication failed with status: {status_value}"

    return True, None


def validate_conditions(assertion):
    conditions = assertion.find("saml:Conditions", SAML_NAMESPACES)
    if conditions is None:
        return True, None

    now = datetime.now(timezone.utc)

    not_before = conditions.get("NotBefore")
    if not_before:
        try:
            nb_time = datetime.fromisoformat(not_before.replace("Z", "+00:00"))
            if now < nb_time:
                return False, "Assertion is not yet valid (NotBefore condition)"
        except ValueError:
            return False, "Invalid NotBefore timestamp format"

    not_on_or_after = conditions.get("NotOnOrAfter")
    if not_on_or_after:
        try:
            noa_time = datetime.fromisoformat(not_on_or_after.replace("Z", "+00:00"))
            if now >= noa_time:
                return False, "Assertion has expired (NotOnOrAfter condition)"
        except ValueError:
            return False, "Invalid NotOnOrAfter timestamp format"

    audience_restriction = conditions.find("saml:AudienceRestriction/saml:Audience", SAML_NAMESPACES)
    if audience_restriction is not None:
        if audience_restriction.text != SP_CONFIG["entity_id"]:
            return False, "Audience mismatch in assertion conditions"

    return True, None


def extract_name_id(assertion):
    subject = assertion.find("saml:Subject/saml:NameID", SAML_NAMESPACES)
    if subject is not None and subject.text:
        return subject.text.strip()
    return None


def extract_attributes(assertion):
    attributes = {}
    attr_statement = assertion.find("saml:AttributeStatement", SAML_NAMESPACES)
    if attr_statement is None:
        return attributes

    for attr in attr_statement.findall("saml:Attribute", SAML_NAMESPACES):
        attr_name = attr.get("Name", "")
        if not attr_name:
            continue
        values = []
        for val in attr.findall("saml:AttributeValue", SAML_NAMESPACES):
            if val.text:
                values.append(val.text.strip())
        if len(values) == 1:
            attributes[attr_name] = values[0]
        elif values:
            attributes[attr_name] = values

    return attributes


def process_saml_response(saml_response_b64):
    root, error = parse_saml_response(saml_response_b64)
    if error:
        return None, error

    ok, error = validate_saml_status(root)
    if not ok:
        return None, error

    assertion = root.find(".//saml:Assertion", SAML_NAMESPACES)
    if assertion is None:
        return None, "No Assertion found in SAML response"

    issuer = assertion.find("saml:Issuer", SAML_NAMESPACES)
    if issuer is None or not issuer.text:
        return None, "Missing Issuer in SAML assertion"
    if issuer.text.strip() != IDP_CONFIG["entity_id"]:
        return None, f"Unexpected assertion issuer: {issuer.text}"

    ok, error = validate_conditions(assertion)
    if not ok:
        return None, error

    name_id = extract_name_id(assertion)
    if not name_id:
        return None, "No NameID found in SAML assertion Subject"

    attributes = extract_attributes(assertion)

    user_data = {
        "name_id": name_id,
        "email": attributes.get("email", attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress", name_id)),
        "first_name": attributes.get("firstName", attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname", "")),
        "last_name": attributes.get("lastName", attributes.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname", "")),
        "roles": attributes.get("roles", attributes.get("http://schemas.microsoft.com/ws/2008/06/identity/claims/role", [])),
        "attributes": attributes,
        "authenticated_at": datetime.now(timezone.utc).isoformat(),
    }

    if isinstance(user_data["roles"], str):
        user_data["roles"] = [user_data["roles"]]

    return user_data, None


@app.route("/")
def index():
    if "user" in session:
        user = session["user"]
        return (
            f"<h1>Welcome, {user.get('first_name', '')} {user.get('last_name', '')}</h1>"
            f"<p>Email: {user.get('email', 'N/A')}</p>"
            f"<p>Roles: {', '.join(user.get('roles', []))}</p>"
            f"<p><a href='/saml/logout'>Logout</a></p>"
        )
    return "<h1>SAML SP Demo</h1><p><a href='/saml/login'>Login via SSO</a></p>"


@app.route("/saml/login")
def saml_login():
    saml_request = f"""<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="_request_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    Version="2.0"
    IssueInstant="{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    AssertionConsumerServiceURL="{SP_CONFIG['acs_url']}"
    Destination="{IDP_CONFIG['sso_url']}">
    <saml:Issuer>{SP_CONFIG['entity_id']}</saml:Issuer>
</samlp:AuthnRequest>"""

    encoded = base64.b64encode(saml_request.encode("utf-8")).decode("utf-8")
    return redirect(f"{IDP_CONFIG['sso_url']}?SAMLRequest={encoded}")


@app.route("/saml/acs", methods=["POST"])
def saml_acs():
    saml_response_b64 = request.form.get("SAMLResponse")
    if not saml_response_b64:
        abort(400, description="Missing SAMLResponse parameter")

    user_data, error = process_saml_response(saml_response_b64)
    if error:
        abort(403, description=f"SAML authentication failed: {error}")

    session["user"] = user_data
    return redirect("/")


@app.route("/saml/logout")
def saml_logout():
    session.pop("user", None)
    return redirect("/")


@app.route("/saml/metadata")
def saml_metadata():
    metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{SP_CONFIG['entity_id']}">
    <md:SPSSODescriptor
        AuthnRequestsSigned="false"
        WantAssertionsSigned="true"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{SP_CONFIG['acs_url']}"
            index="0"
            isDefault="true"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
    return metadata, 200, {"Content-Type": "application/xml"}


@app.route("/dashboard")
@login_required
def dashboard():
    user = session["user"]
    return (
        f"<h1>Dashboard</h1>"
        f"<p>Logged in as: {user['email']}</p>"
        f"<p>Session started: {user['authenticated_at']}</p>"
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)