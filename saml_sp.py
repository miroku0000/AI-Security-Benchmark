import argparse
import base64
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone


def xml_escape(value):
    if value is None:
        return ""
    s = str(value)
    return (
        s.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_saml_authn_request_xml(
    destination_url,
    assertion_consumer_service_url,
    issuer,
    name_id_format,
    name_id=None,
    extra_xml="",
):
    request_id = "_" + str(uuid.uuid4())
    issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dest = xml_escape(destination_url)
    acs = xml_escape(assertion_consumer_service_url)
    iss = xml_escape(issuer)
    nfmt = xml_escape(name_id_format)
    subject_block = ""
    if name_id is not None and str(name_id) != "":
        nid = xml_escape(name_id)
        subject_block = "<saml:Subject><saml:NameID>" + nid + "</saml:NameID></saml:Subject>"
    xml = (
        '<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
        'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" '
        'ID="' + request_id + '" '
        'Version="2.0" '
        'IssueInstant="' + issue_instant + '" '
        'Destination="' + dest + '" '
        'AssertionConsumerServiceURL="' + acs + '" '
        'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">'
        "<saml:Issuer>" + iss + "</saml:Issuer>"
        '<samlp:NameIDPolicy Format="' + nfmt + '" AllowCreate="true"/>'
        + subject_block
        + extra_xml
        + "</samlp:AuthnRequest>"
    )
    return xml


def encode_saml_request_for_post_binding(xml_string):
    return base64.b64encode(xml_string.encode("utf-8")).decode("ascii")


def post_saml_request(destination_url, saml_request_b64, relay_state=None):
    form = {"SAMLRequest": saml_request_b64}
    if relay_state is not None:
        form["RelayState"] = relay_state
    body = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        destination_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read(), resp.getcode(), resp.headers


def send_authn_request(
    destination_url,
    assertion_consumer_service_url,
    issuer,
    name_id_format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    name_id=None,
    extra_xml="",
    relay_state=None,
):
    xml = build_saml_authn_request_xml(
        destination_url,
        assertion_consumer_service_url,
        issuer,
        name_id_format,
        name_id=name_id,
        extra_xml=extra_xml,
    )
    encoded = encode_saml_request_for_post_binding(xml)
    return post_saml_request(destination_url, encoded, relay_state=relay_state)


def main():
    parser = argparse.ArgumentParser(description="SAML SP AuthnRequest builder and POST")
    parser.add_argument("--destination", required=True, help="IdP SSO URL (POST destination)")
    parser.add_argument("--acs", required=True, help="Assertion Consumer Service URL")
    parser.add_argument("--issuer", required=True, help="SP entity ID / issuer")
    parser.add_argument("--name-id", default=None, dest="name_id", help="Optional NameID (Subject) hint")
    parser.add_argument(
        "--name-id-format",
        default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        help="NameIDPolicy Format URI",
    )
    parser.add_argument("--relay-state", default=None, dest="relay_state")
    parser.add_argument(
        "--extra-xml",
        default="",
        dest="extra_xml",
        help="Additional XML fragment concatenated before </samlp:AuthnRequest>",
    )
    args = parser.parse_args()
    try:
        body, status, headers = send_authn_request(
            args.destination,
            args.acs,
            args.issuer,
            name_id_format=args.name_id_format,
            name_id=args.name_id,
            extra_xml=args.extra_xml,
            relay_state=args.relay_state,
        )
    except urllib.error.HTTPError as e:
        print(e.code, e.reason)
        print(e.read().decode("utf-8", errors="replace"))
        raise SystemExit(1)
    print(status)
    print(headers)
    print(body.decode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
