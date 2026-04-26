import base64
import binascii
import os
import secrets
import urllib.parse
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from flask import Flask, abort, jsonify, redirect, request, session, url_for
from signxml import InvalidSignature, XMLVerifier

NS = {
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}

MAX_SAML_RESPONSE_BYTES = 200_000
SAML_TIME_SKEW = timedelta(minutes=2)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def format_saml_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def parse_saml_time(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def require_env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_idp_certificate() -> str:
    cert_path = Path(require_env("SAML_IDP_CERT_PATH"))
    return cert_path.read_text(encoding="utf-8")


def reject_unsafe_xml(raw_xml: bytes) -> None:
    probe = raw_xml[:4096].lower()
    if b"<!doctype" in probe or b"<!entity" in probe:
        raise ValueError("SAML response contains prohibited XML declarations")


def decode_saml_response(encoded_response: str) -> bytes:
    try:
        decoded = base64.b64decode(encoded_response, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("SAMLResponse is not valid base64") from exc

    if not decoded:
        raise ValueError("SAMLResponse is empty")
    if len(decoded) > MAX_SAML_RESPONSE_BYTES:
        raise ValueError("SAMLResponse exceeds maximum size")

    reject_unsafe_xml(decoded)
    return decoded


def parse_xml(raw_xml: bytes) -> ET.Element:
    return ET.fromstring(raw_xml, parser=ET.XMLParser())


def build_authn_request_xml(request_id: str) -> bytes:
    root = ET.Element(
        ET.QName(NS["samlp"], "AuthnRequest"),
        {
            "ID": request_id,
            "Version": "2.0",
            "IssueInstant": format_saml_timestamp(utcnow()),
            "Destination": require_env("SAML_IDP_SSO_URL"),
            "ProtocolBinding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            "AssertionConsumerServiceURL": require_env("SAML_ACS_URL"),
        },
    )
    issuer = ET.SubElement(root, ET.QName(NS["saml"], "Issuer"))
    issuer.text = require_env("SAML_SP_ENTITY_ID")
    ET.SubElement(
        root,
        ET.QName(NS["samlp"], "NameIDPolicy"),
        {
            "AllowCreate": "true",
            "Format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        },
    )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def deflate_and_base64(xml_bytes: bytes) -> str:
    compressor = zlib.compressobj(wbits=-15)
    payload = compressor.compress(xml_bytes) + compressor.flush()
    return base64.b64encode(payload).decode("ascii")


def normalize_relay_state(value: str | None) -> str | None:
    if not value:
        return None
    target = urllib.parse.urlparse(urllib.parse.urljoin(request.host_url, value))
    origin = urllib.parse.urlparse(request.host_url)
    if target.scheme != origin.scheme or target.netloc != origin.netloc:
        raise ValueError("RelayState must be relative or same-origin")
    normalized = urllib.parse.urlunparse(("", "", target.path or "/", target.params, target.query, ""))
    return normalized


def get_assertion(root: ET.Element) -> ET.Element:
    assertions = root.findall("./saml:Assertion", NS)
    if not assertions:
        raise ValueError("SAML response does not contain an Assertion")
    if len(assertions) != 1:
        raise ValueError("SAML response must contain exactly one Assertion")
    return assertions[0]


def validate_response_success(root: ET.Element) -> None:
    status_code = root.find("./samlp:Status/samlp:StatusCode", NS)
    if status_code is None:
        raise ValueError("SAML response is missing a StatusCode")
    if status_code.attrib.get("Value") != "urn:oasis:names:tc:SAML:2.0:status:Success":
        raise ValueError("SAML response status is not Success")


def validate_destination(root: ET.Element) -> None:
    destination = root.attrib.get("Destination")
    expected_destination = require_env("SAML_ACS_URL")
    if destination and destination != expected_destination:
        raise ValueError("SAML response destination does not match the ACS URL")


def validate_issuer(root: ET.Element, assertion: ET.Element) -> None:
    expected_issuer = os.environ.get("SAML_IDP_ENTITY_ID")
    if not expected_issuer:
        return
    response_issuer = root.findtext("./saml:Issuer", default="", namespaces=NS)
    assertion_issuer = assertion.findtext("./saml:Issuer", default="", namespaces=NS)
    if expected_issuer not in {response_issuer, assertion_issuer}:
        raise ValueError("SAML response issuer does not match the configured IdP")


def verify_signature(raw_xml: bytes, root: ET.Element, assertion: ET.Element) -> None:
    has_response_signature = root.find("./ds:Signature", NS) is not None
    has_assertion_signature = root.find("./saml:Assertion/ds:Signature", NS) is not None
    if not has_response_signature and not has_assertion_signature:
        raise ValueError("SAML response is not signed")

    try:
        result = XMLVerifier().verify(
            raw_xml,
            x509_cert=load_idp_certificate(),
            id_attribute="ID",
        )
    except InvalidSignature as exc:
        raise ValueError("SAML signature verification failed") from exc

    signed_name = local_name(result.signed_xml.tag)
    if signed_name not in {"Response", "Assertion"}:
        raise ValueError("Unexpected signed XML element in SAML response")

    if signed_name == "Assertion":
        signed_id = result.signed_xml.get("ID")
        assertion_id = assertion.attrib.get("ID")
        if not signed_id or signed_id != assertion_id:
            raise ValueError("Signed assertion does not match the processed Assertion")


def validate_in_response_to(root: ET.Element, assertion: ET.Element) -> None:
    expected_request_id = session.get("saml_request_id")
    if not expected_request_id:
        return

    response_reference = root.attrib.get("InResponseTo")
    confirmation_data = assertion.find(
        "./saml:Subject/saml:SubjectConfirmation/saml:SubjectConfirmationData",
        NS,
    )
    confirmation_reference = None if confirmation_data is None else confirmation_data.attrib.get("InResponseTo")

    if response_reference != expected_request_id and confirmation_reference != expected_request_id:
        raise ValueError("SAML response does not match the outstanding authentication request")


def validate_conditions(assertion: ET.Element) -> None:
    now = utcnow()
    conditions = assertion.find("./saml:Conditions", NS)
    if conditions is None:
        raise ValueError("Assertion is missing Conditions")

    not_before = parse_saml_time(conditions.attrib.get("NotBefore"))
    not_on_or_after = parse_saml_time(conditions.attrib.get("NotOnOrAfter"))

    if not_before and now + SAML_TIME_SKEW < not_before:
        raise ValueError("Assertion is not yet valid")
    if not_on_or_after and now >= not_on_or_after + SAML_TIME_SKEW:
        raise ValueError("Assertion has expired")

    expected_audience = os.environ.get("SAML_AUDIENCE") or require_env("SAML_SP_ENTITY_ID")
    audience = conditions.find("./saml:AudienceRestriction/saml:Audience", NS)
    if audience is None or audience.text != expected_audience:
        raise ValueError("Assertion audience does not match this service provider")


def validate_subject_confirmation(assertion: ET.Element) -> None:
    confirmation = assertion.find("./saml:Subject/saml:SubjectConfirmation", NS)
    if confirmation is None:
        raise ValueError("Assertion is missing SubjectConfirmation")
    if confirmation.attrib.get("Method") != "urn:oasis:names:tc:SAML:2.0:cm:bearer":
        raise ValueError("Assertion SubjectConfirmation method must be bearer")

    confirmation_data = confirmation.find("./saml:SubjectConfirmationData", NS)
    if confirmation_data is None:
        raise ValueError("Assertion is missing SubjectConfirmationData")

    recipient = confirmation_data.attrib.get("Recipient")
    if recipient and recipient != require_env("SAML_ACS_URL"):
        raise ValueError("Assertion recipient does not match the ACS URL")

    not_on_or_after = parse_saml_time(confirmation_data.attrib.get("NotOnOrAfter"))
    if not_on_or_after and utcnow() >= not_on_or_after + SAML_TIME_SKEW:
        raise ValueError("Assertion subject confirmation has expired")


def extract_attributes(assertion: ET.Element) -> dict[str, Any]:
    attributes: dict[str, Any] = {}
    for attribute in assertion.findall(".//saml:Attribute", NS):
        name = attribute.attrib.get("Name")
        if not name:
            continue
        values = [value.text or "" for value in attribute.findall("./saml:AttributeValue", NS)]
        if not values:
            attributes[name] = ""
        elif len(values) == 1:
            attributes[name] = values[0]
        else:
            attributes[name] = values
    return attributes


def extract_session_data(assertion: ET.Element) -> dict[str, Any]:
    name_id = assertion.findtext("./saml:Subject/saml:NameID", default="", namespaces=NS)
    if not name_id:
        raise ValueError("Assertion is missing NameID")

    authn_statement = assertion.find("./saml:AuthnStatement", NS)
    session_index = None if authn_statement is None else authn_statement.attrib.get("SessionIndex")

    return {
        "name_id": name_id,
        "session_index": session_index,
        "attributes": extract_attributes(assertion),
        "authenticated_at": format_saml_timestamp(utcnow()),
    }


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") != "development",
    )

    @app.get("/")
    def index():
        return jsonify(
            {
                "authenticated": "user" in session,
                "user": session.get("user"),
                "login_url": url_for("login", _external=True),
                "logout_url": url_for("logout", _external=True),
                "acs_url": url_for("acs", _external=True),
                "metadata_url": url_for("metadata", _external=True),
            }
        )

    @app.get("/login")
    def login():
        request_id = "_" + secrets.token_urlsafe(32)
        relay_state = normalize_relay_state(request.args.get("next"))
        session["saml_request_id"] = request_id
        if relay_state:
            session["relay_state"] = relay_state
        else:
            session.pop("relay_state", None)

        query = {"SAMLRequest": deflate_and_base64(build_authn_request_xml(request_id))}
        if relay_state:
            query["RelayState"] = relay_state
        return redirect(require_env("SAML_IDP_SSO_URL") + "?" + urllib.parse.urlencode(query), code=302)

    @app.post("/saml/acs")
    def acs():
        encoded_response = request.form.get("SAMLResponse", "")
        if not encoded_response:
            abort(400, description="Missing SAMLResponse form field")

        raw_xml = decode_saml_response(encoded_response)
        root = parse_xml(raw_xml)

        if local_name(root.tag) != "Response":
            raise ValueError("SAML payload root element must be Response")

        assertion = get_assertion(root)
        validate_response_success(root)
        validate_destination(root)
        validate_issuer(root, assertion)
        verify_signature(raw_xml, root, assertion)
        validate_in_response_to(root, assertion)
        validate_conditions(assertion)
        validate_subject_confirmation(assertion)

        relay_state = normalize_relay_state(request.form.get("RelayState")) or session.get("relay_state")
        user = extract_session_data(assertion)

        session.clear()
        session["user"] = user

        if relay_state:
            return redirect(relay_state, code=302)
        return jsonify({"authenticated": True, "user": user})

    @app.get("/me")
    def me():
        user = session.get("user")
        if not user:
            abort(401, description="Not authenticated")
        return jsonify(user)

    @app.route("/logout", methods=["GET", "POST"])
    def logout():
        session.clear()
        return jsonify({"authenticated": False})

    @app.get("/metadata")
    def metadata():
        entity_id = require_env("SAML_SP_ENTITY_ID")
        acs_url = require_env("SAML_ACS_URL")

        root = ET.Element(ET.QName(NS["md"], "EntityDescriptor"), {"entityID": entity_id})
        sp_descriptor = ET.SubElement(
            root,
            ET.QName(NS["md"], "SPSSODescriptor"),
            {
                "AuthnRequestsSigned": "false",
                "WantAssertionsSigned": "true",
                "protocolSupportEnumeration": "urn:oasis:names:tc:SAML:2.0:protocol",
            },
        )
        ET.SubElement(
            sp_descriptor,
            ET.QName(NS["md"], "AssertionConsumerService"),
            {
                "Binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                "Location": acs_url,
                "index": "0",
                "isDefault": "true",
            },
        )
        metadata_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        return app.response_class(metadata_xml, mimetype="application/samlmetadata+xml")

    @app.errorhandler(ValueError)
    def handle_value_error(error: ValueError):
        return jsonify({"error": str(error)}), 400

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))