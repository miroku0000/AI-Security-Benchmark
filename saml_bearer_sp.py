#!/usr/bin/env python3
import base64
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import lxml.etree as etree
from flask import Flask, redirect, request, session, url_for

BEARER_METHOD = "urn:oasis:names:tc:SAML:2.0:cm:bearer"


def _local_xpath(root: etree._Element, tag: str) -> List[etree._Element]:
    return root.xpath(f".//*[local-name()='{tag}']")


def _decode_saml_response(raw: str) -> bytes:
    s = raw.strip()
    s = re.sub(r"\s+", "", s)
    pad = (-len(s)) % 4
    if pad:
        s += "=" * pad
    return base64.b64decode(s, validate=False)


def _parse_xs_datetime(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def conditions_not_violated(assertion: etree._Element) -> bool:
    conds = _local_xpath(assertion, "Conditions")
    if not conds:
        return True
    c = conds[0]
    now = datetime.now(timezone.utc)
    nb = _parse_xs_datetime(c.get("NotBefore"))
    na = _parse_xs_datetime(c.get("NotOnOrAfter"))
    if nb is not None and now < nb:
        return False
    if na is not None and now > na:
        return False
    return True


def has_bearer_subject_confirmation(assertion: etree._Element) -> bool:
    for sc in _local_xpath(assertion, "SubjectConfirmation"):
        if sc.get("Method") == BEARER_METHOD:
            return True
    return False


def extract_first_assertion(root: etree._Element) -> etree._Element:
    assertions = _local_xpath(root, "Assertion")
    if not assertions:
        raise ValueError("No SAML Assertion found in response")
    return assertions[0]


def extract_name_id(assertion: etree._Element) -> Optional[str]:
    for subj in _local_xpath(assertion, "Subject"):
        for nid in _local_xpath(subj, "NameID"):
            t = (nid.text or "").strip()
            if t:
                return t
            inner = "".join(nid.itertext()).strip()
            if inner:
                return inner
    return None


def extract_session_index(assertion: etree._Element) -> Optional[str]:
    for st in _local_xpath(assertion, "AuthnStatement"):
        idx = st.get("SessionIndex")
        if idx:
            return idx
    return None


def extract_attributes(assertion: etree._Element) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for attr in _local_xpath(assertion, "Attribute"):
        name = attr.get("Name")
        if not name:
            continue
        vals: List[str] = []
        for av in _local_xpath(attr, "AttributeValue"):
            if av.text:
                vals.append(av.text.strip())
            else:
                vals.append("".join(av.itertext()).strip())
        if name not in out:
            out[name] = []
        out[name].extend([v for v in vals if v != ""])
    return out


def parse_saml_response_xml(xml_bytes: bytes) -> Dict[str, Any]:
    root = etree.fromstring(xml_bytes)
    assertion = extract_first_assertion(root)
    if not has_bearer_subject_confirmation(assertion):
        raise ValueError("Assertion must include bearer SubjectConfirmation")
    if os.environ.get("SAML_CHECK_CONDITIONS", "0") not in ("0", "false", "False"):
        if not conditions_not_violated(assertion):
            raise ValueError("SAML Assertion Conditions are not satisfied")
    name_id = extract_name_id(assertion)
    attrs = extract_attributes(assertion)
    sess_idx = extract_session_index(assertion)
    issuer_els = _local_xpath(assertion, "Issuer")
    issuer = issuer_els[0].text.strip() if issuer_els and issuer_els[0].text else None
    return {
        "name_id": name_id,
        "session_index": sess_idx,
        "issuer": issuer,
        "attributes": attrs,
        "assertion_xml_id": assertion.get("ID"),
    }


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32).hex())

    @app.route("/health")
    def health():
        return "ok", 200

    @app.route("/acs", methods=["POST"])
    def assertion_consumer_service():
        saml_b64 = request.form.get("SAMLResponse")
        if not saml_b64:
            return "Missing SAMLResponse", 400
        relay = request.form.get("RelayState")
        try:
            raw_xml = _decode_saml_response(saml_b64)
        except Exception:
            return "Invalid SAMLResponse encoding", 400
        try:
            user = parse_saml_response_xml(raw_xml)
        except Exception as e:
            return f"SAML validation failed: {e}", 400
        session["user"] = {
            "name_id": user["name_id"],
            "session_index": user["session_index"],
            "issuer": user["issuer"],
            "attributes": user["attributes"],
            "relay_state": relay,
            "authenticated_at": datetime.now(timezone.utc).isoformat(),
        }
        session["user_id"] = user["name_id"] or str(uuid.uuid4())
        return redirect(os.environ.get("SAML_LOGIN_SUCCESS_URL", "/whoami"))

    @app.route("/whoami")
    def whoami():
        u = session.get("user")
        if not u:
            return "not authenticated", 401
        return {"user": u}, 200

    @app.route("/logout", methods=["GET", "POST"])
    def logout():
        session.clear()
        return redirect(url_for("health"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")))
