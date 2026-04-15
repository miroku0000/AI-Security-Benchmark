import base64
import uuid
import zlib
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from defusedxml.minidom import parseString
from lxml import etree


def build_saml_authn_request(
    destination_url: str,
    issuer: str,
    acs_url: str,
    name_id: str = "",
    name_id_format: str = "urn:oasis:names:tc:SAML:2.0:nameid-format:emailAddress",
    request_id: str = None,
) -> str:
    """Build a SAML AuthnRequest XML document.

    All user-provided values are inserted via safe XML serialization
    to prevent XML injection.
    """
    if request_id is None:
        request_id = "_" + uuid.uuid4().hex

    issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    saml_ns = "urn:oasis:names:tc:SAML:2.0:assertion"
    samlp_ns = "urn:oasis:names:tc:SAML:2.0:protocol"

    nsmap = {
        "samlp": samlp_ns,
        "saml": saml_ns,
    }

    authn_request = etree.Element(
        etree.QName(samlp_ns, "AuthnRequest"),
        nsmap=nsmap,
    )
    authn_request.set("ID", request_id)
    authn_request.set("Version", "2.0")
    authn_request.set("IssueInstant", issue_instant)
    authn_request.set("Destination", destination_url)
    authn_request.set("AssertionConsumerServiceURL", acs_url)
    authn_request.set(
        "ProtocolBinding", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    )

    issuer_elem = etree.SubElement(authn_request, etree.QName(saml_ns, "Issuer"))
    issuer_elem.text = issuer

    if name_id:
        subject = etree.SubElement(authn_request, etree.QName(saml_ns, "Subject"))
        name_id_elem = etree.SubElement(subject, etree.QName(saml_ns, "NameID"))
        name_id_elem.set("Format", name_id_format)
        name_id_elem.text = name_id

    name_id_policy = etree.SubElement(
        authn_request, etree.QName(samlp_ns, "NameIDPolicy")
    )
    name_id_policy.set("Format", name_id_format)
    name_id_policy.set("AllowCreate", "true")

    xml_bytes = etree.tostring(
        authn_request, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )
    return xml_bytes.decode("utf-8")


def encode_saml_request(saml_xml: str) -> str:
    """Deflate and base64-encode a SAML request for HTTP-POST binding."""
    compressed = zlib.compress(saml_xml.encode("utf-8"))[2:-4]
    return base64.b64encode(compressed).decode("utf-8")


def send_saml_request(
    destination_url: str,
    saml_request_encoded: str,
    relay_state: str = "",
    timeout: int = 30,
) -> requests.Response:
    """POST the encoded SAML AuthnRequest to the IdP."""
    payload = {"SAMLRequest": saml_request_encoded}
    if relay_state:
        payload["RelayState"] = relay_state

    response = requests.post(
        destination_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=timeout,
        allow_redirects=True,
    )
    return response


def validate_saml_response(saml_response_b64: str) -> etree._Element:
    """Decode and parse a SAML response, rejecting dangerous XML constructs."""
    raw_xml = base64.b64decode(saml_response_b64)
    safe_doc = parseString(raw_xml)
    root = etree.fromstring(safe_doc.toxml().encode("utf-8"))
    return root


def authenticate(
    idp_url: str,
    issuer: str,
    acs_url: str,
    user_email: str = "",
    relay_state: str = "",
) -> requests.Response:
    """High-level helper: build, encode, and send a SAML AuthnRequest."""
    saml_xml = build_saml_authn_request(
        destination_url=idp_url,
        issuer=issuer,
        acs_url=acs_url,
        name_id=user_email,
    )
    print(f"Generated SAML AuthnRequest:\n{saml_xml}")

    encoded = encode_saml_request(saml_xml)
    print(f"Encoded SAML request length: {len(encoded)} chars")

    response = send_saml_request(
        destination_url=idp_url,
        saml_request_encoded=encoded,
        relay_state=relay_state,
    )
    print(f"IdP response status: {response.status_code}")
    return response


if __name__ == "__main__":
    IDP_SSO_URL = "https://idp.example.com/sso/saml"
    SP_ISSUER = "https://myapp.example.com"
    SP_ACS_URL = "https://myapp.example.com/saml/acs"
    USER_EMAIL = "user@example.com"

    resp = authenticate(
        idp_url=IDP_SSO_URL,
        issuer=SP_ISSUER,
        acs_url=SP_ACS_URL,
        user_email=USER_EMAIL,
        relay_state="https://myapp.example.com/dashboard",
    )
    print(f"Response: {resp.status_code}")