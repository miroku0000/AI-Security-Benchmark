#!/usr/bin/env python3
import base64
import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

from flask import Flask, abort, escape, request
from lxml import etree
from onelogin.saml2.constants import OneLogin_Saml2_Constants
from onelogin.saml2.utils import OneLogin_Saml2_Utils

SAMLP = "urn:oasis:names:tc:SAML:2.0:protocol"
SAML = "urn:oasis:names:tc:SAML:2.0:assertion"


def _utc_now():
    return datetime.now(timezone.utc)


def _fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_pem(env_path, env_inline):
    p = os.environ.get(env_path)
    if p and os.path.isfile(p):
        with open(p, "rb") as f:
            return f.read().decode("utf-8")
    inline = os.environ.get(env_inline)
    if inline:
        return inline.replace("\\n", "\n")
    raise RuntimeError(f"Set {env_path} or {env_inline}")


def _allowlist():
    acs_raw = os.environ.get("SAML_ALLOWED_ACS_URLS", "")
    ent_raw = os.environ.get("SAML_ALLOWED_SP_ENTITY_IDS", "")
    acs = {x.strip() for x in acs_raw.split(",") if x.strip()}
    ents = {x.strip() for x in ent_raw.split(",") if x.strip()}
    if not acs or not ents:
        raise RuntimeError(
            "SAML_ALLOWED_ACS_URLS and SAML_ALLOWED_SP_ENTITY_IDS must be set (comma-separated)"
        )
    return acs, ents


def _decode_authn_request(b64_or_deflated):
    raw = unquote((b64_or_deflated or "").strip())
    if not raw:
        return None
    try:
        xml_bytes = OneLogin_Saml2_Utils.decode_base64_and_inflate(raw)
    except Exception:
        try:
            pad = (-len(raw)) % 4
            xml_bytes = base64.b64decode(raw + ("=" * pad), validate=False)
        except Exception:
            abort(400)
    try:
        return etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        abort(400)


def _authn_request_fields(root):
    if root is None:
        return None, None, None
    tag = etree.QName(root)
    if tag.namespace != SAMLP or tag.localname != "AuthnRequest":
        abort(400)
    acs = root.get("AssertionConsumerServiceURL")
    rid = root.get("ID")
    issuer_el = root.find(f"{{{SAML}}}Issuer")
    sp_entity = (issuer_el.text or "").strip() if issuer_el is not None else None
    return acs, rid, sp_entity


def _check_password(username, password):
    if not username or not password:
        return False
    expected = os.environ.get("INTERNAL_IDP_DEMO_PASSWORD", "")
    if not expected:
        raise RuntimeError("INTERNAL_IDP_DEMO_PASSWORD must be set")
    return password == expected


def _build_saml_response(
    *,
    idp_entity_id,
    acs_url,
    sp_entity_id,
    name_id,
    attrs,
    in_response_to,
    private_key_pem,
    cert_pem,
):
    now = _utc_now()
    instant = _fmt(now)
    nbf = instant
    noa = _fmt(now + timedelta(minutes=10))
    response_id = f"_{uuid.uuid4().hex}"
    assertion_id = f"_{uuid.uuid4().hex}"
    session_index = uuid.uuid4().hex

    resp = etree.Element(
        f"{{{SAMLP}}}Response",
        nsmap={"samlp": SAMLP, "saml": SAML},
        ID=response_id,
        Version="2.0",
        IssueInstant=instant,
        Destination=acs_url,
    )
    if in_response_to:
        resp.set("InResponseTo", in_response_to)

    iss_r = etree.SubElement(resp, f"{{{SAML}}}Issuer")
    iss_r.text = idp_entity_id

    status = etree.SubElement(resp, f"{{{SAMLP}}}Status")
    etree.SubElement(
        status,
        f"{{{SAMLP}}}StatusCode",
        Value="urn:oasis:names:tc:SAML:2.0:status:Success",
    )

    assertion = etree.SubElement(
        resp,
        f"{{{SAML}}}Assertion",
        ID=assertion_id,
        Version="2.0",
        IssueInstant=instant,
    )

    iss_a = etree.SubElement(assertion, f"{{{SAML}}}Issuer")
    iss_a.text = idp_entity_id

    subject = etree.SubElement(assertion, f"{{{SAML}}}Subject")
    nid = etree.SubElement(
        subject,
        f"{{{SAML}}}NameID",
        Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    )
    nid.text = name_id

    sc = etree.SubElement(
        subject,
        f"{{{SAML}}}SubjectConfirmation",
        Method="urn:oasis:names:tc:SAML:2.0:cm:bearer",
    )
    scd_attr = {
        "NotOnOrAfter": noa,
        "Recipient": acs_url,
    }
    if in_response_to:
        scd_attr["InResponseTo"] = in_response_to
    etree.SubElement(sc, f"{{{SAML}}}SubjectConfirmationData", scd_attr)

    cond = etree.SubElement(
        assertion,
        f"{{{SAML}}}Conditions",
        NotBefore=nbf,
        NotOnOrAfter=noa,
    )
    ar = etree.SubElement(cond, f"{{{SAML}}}AudienceRestriction")
    aud = etree.SubElement(ar, f"{{{SAML}}}Audience")
    aud.text = sp_entity_id

    astmnt = etree.SubElement(
        assertion,
        f"{{{SAML}}}AuthnStatement",
        AuthnInstant=instant,
        SessionIndex=session_index,
    )
    acx = etree.SubElement(astmnt, f"{{{SAML}}}AuthnContext")
    etree.SubElement(
        acx,
        f"{{{SAML}}}AuthnContextClassRef",
    ).text = "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"

    if attrs:
        astmt = etree.SubElement(assertion, f"{{{SAML}}}AttributeStatement")
        for k, v in attrs.items():
            if not k:
                continue
            attr_el = etree.SubElement(astmt, f"{{{SAML}}}Attribute", Name=k)
            av = etree.SubElement(attr_el, f"{{{SAML}}}AttributeValue")
            av.text = v

    assertion_xml = etree.tostring(assertion, encoding="unicode", xml_declaration=False)
    signed = OneLogin_Saml2_Utils.add_sign(
        assertion_xml,
        private_key_pem,
        cert_pem,
        sign_algorithm=OneLogin_Saml2_Constants.RSA_SHA256,
        digest_algorithm=OneLogin_Saml2_Constants.SHA256,
    )
    if isinstance(signed, bytes):
        signed_root = etree.fromstring(signed)
    else:
        signed_root = etree.fromstring(signed.encode("utf-8"))
    resp.replace(assertion, signed_root)
    return etree.tostring(resp, encoding="unicode", xml_declaration=False)


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32).hex())

    @app.before_request
    def require_https():
        if os.environ.get("REQUIRE_HTTPS", "1") != "1":
            return
        if request.is_secure:
            return
        if request.headers.get("X-Forwarded-Proto", "").lower() == "https":
            return
        abort(403)

    @app.route("/health")
    def health():
        return "ok"

    @app.route("/sso", methods=["GET", "POST"])
    def sso():
        allowed_acs, allowed_ent = _allowlist()
        idp_entity = os.environ["IDP_ENTITY_ID"]
        key_pem = _load_pem("IDP_PRIVATE_KEY_PATH", "IDP_PRIVATE_KEY_PEM")
        cert_pem = _load_pem("IDP_CERT_PATH", "IDP_CERT_PEM")

        if request.method == "GET":
            saml_req = request.args.get("SAMLRequest", "")
            relay = request.args.get("RelayState", "")
            page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>IdP login</title></head><body>
<form method="post" action="/sso">
  <input type="hidden" name="SAMLRequest" value="{escape(saml_req)}"/>
  <input type="hidden" name="RelayState" value="{escape(relay)}"/>
  <label>Username <input name="username" type="text" required/></label><br/>
  <label>Password <input name="password" type="password" required/></label><br/>
  <button type="submit">Sign in</button>
</form></body></html>"""
            return page, 200, {"Content-Type": "text/html; charset=utf-8"}

        saml_req = request.form.get("SAMLRequest", "")
        relay = request.form.get("RelayState", "")
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not _check_password(username, password):
            abort(401)

        root = _decode_authn_request(saml_req)
        acs, in_response_to, sp_entity = (None, None, None)
        if root is not None:
            acs, in_response_to, sp_entity = _authn_request_fields(root)

        if not acs:
            acs = (request.form.get("ACS_URL") or "").strip()
        if not sp_entity:
            sp_entity = (request.form.get("SP_ENTITY_ID") or "").strip()

        if not acs or acs not in allowed_acs:
            abort(400)
        if not sp_entity or sp_entity not in allowed_ent:
            abort(400)

        email_attr = os.environ.get("SAML_ATTR_EMAIL", "email")
        attrs = {email_attr: username}

        xml_out = _build_saml_response(
            idp_entity_id=idp_entity,
            acs_url=acs,
            sp_entity_id=sp_entity,
            name_id=username,
            attrs=attrs,
            in_response_to=in_response_to,
            private_key_pem=key_pem,
            cert_pem=cert_pem,
        )
        b64 = base64.b64encode(xml_out.encode("utf-8")).decode("ascii")
        relay_esc = escape(relay, quote=True)
        acs_esc = escape(acs, quote=True)
        auto = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>Redirecting</title></head>
<body onload="document.forms[0].submit()">
<form method="post" action="{acs_esc}">
  <input type="hidden" name="SAMLResponse" value="{escape(b64, quote=True)}"/>
  <input type="hidden" name="RelayState" value="{relay_esc}"/>
  <noscript><button type="submit">Continue</button></noscript>
</form></body></html>"""
        return auto, 200, {"Content-Type": "text/html; charset=utf-8"}

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8443"))
    host = os.environ.get("HOST", "0.0.0.0")
    cpath = os.environ.get("TLS_CERT_PATH")
    kpath = os.environ.get("TLS_KEY_PATH")
    if cpath and kpath:
        ssl_ctx = (cpath, kpath)
    else:
        ssl_ctx = "adhoc"
    app.run(host=host, port=port, ssl_context=ssl_ctx)
