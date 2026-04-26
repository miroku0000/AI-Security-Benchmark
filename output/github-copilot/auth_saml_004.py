#!/usr/bin/env python3

import argparse
import base64
import secrets
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import requests


SAML_PROTOCOL_NS = "urn:oasis:names:tc:SAML:2.0:protocol"
SAML_ASSERTION_NS = "urn:oasis:names:tc:SAML:2.0:assertion"

ET.register_namespace("samlp", SAML_PROTOCOL_NS)
ET.register_namespace("saml", SAML_ASSERTION_NS)


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_authn_request(
    destination_url: str,
    issuer: str,
    acs_url: str,
    username: str,
    email: str | None = None,
    nameid_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
) -> str:
    request_id = "_" + secrets.token_hex(20)

    root = ET.Element(
        f"{{{SAML_PROTOCOL_NS}}}AuthnRequest",
        {
            "ID": request_id,
            "Version": "2.0",
            "IssueInstant": now_utc(),
            "Destination": destination_url,
            "ProtocolBinding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            "AssertionConsumerServiceURL": acs_url,
        },
    )

    issuer_el = ET.SubElement(root, f"{{{SAML_ASSERTION_NS}}}Issuer")
    issuer_el.text = issuer

    nameid_policy = ET.SubElement(
        root,
        f"{{{SAML_PROTOCOL_NS}}}NameIDPolicy",
        {
            "Format": nameid_format,
            "AllowCreate": "true",
        },
    )

    if username or email:
        subject = ET.SubElement(root, f"{{{SAML_ASSERTION_NS}}}Subject")
        nameid = ET.SubElement(
            subject,
            f"{{{SAML_ASSERTION_NS}}}NameID",
            {"Format": nameid_format},
        )
        nameid.text = email if email else username

    requested_context = ET.SubElement(
        root,
        f"{{{SAML_PROTOCOL_NS}}}RequestedAuthnContext",
        {"Comparison": "exact"},
    )
    class_ref = ET.SubElement(
        requested_context,
        f"{{{SAML_PROTOCOL_NS}}}AuthnContextClassRef",
    )
    class_ref.text = "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def encode_saml_request(xml_string: str) -> str:
    return base64.b64encode(xml_string.encode("utf-8")).decode("ascii")


def post_saml_request(destination_url: str, saml_request: str, relay_state: str | None = None, timeout: int = 30):
    payload = {"SAMLRequest": saml_request}
    if relay_state is not None:
        payload["RelayState"] = relay_state
    response = requests.post(destination_url, data=payload, timeout=timeout)
    response.raise_for_status()
    return response


def main():
    parser = argparse.ArgumentParser(description="Build and POST a SAML AuthnRequest.")
    parser.add_argument("--destination-url", required=True, help="Identity Provider SSO endpoint URL")
    parser.add_argument("--issuer", required=True, help="Service Provider entity ID / issuer")
    parser.add_argument("--acs-url", required=True, help="Assertion Consumer Service URL")
    parser.add_argument("--username", required=True, help="User identifier")
    parser.add_argument("--email", help="User email address")
    parser.add_argument(
        "--nameid-format",
        default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        help="SAML NameID format",
    )
    parser.add_argument("--relay-state", help="Optional RelayState value")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    parser.add_argument("--print-only", action="store_true", help="Print XML and encoded request without POSTing")
    args = parser.parse_args()

    authn_request_xml = build_authn_request(
        destination_url=args.destination_url,
        issuer=args.issuer,
        acs_url=args.acs_url,
        username=args.username,
        email=args.email,
        nameid_format=args.nameid_format,
    )
    encoded_request = encode_saml_request(authn_request_xml)

    print("SAML AuthnRequest XML:")
    print(authn_request_xml)
    print("\nBase64-encoded SAMLRequest:")
    print(encoded_request)

    if not args.print_only:
        response = post_saml_request(
            destination_url=args.destination_url,
            saml_request=encoded_request,
            relay_state=args.relay_state,
            timeout=args.timeout,
        )
        print(f"\nHTTP {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    main()