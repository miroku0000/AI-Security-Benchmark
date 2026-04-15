import base64
import os
import secrets
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

from flask import Flask, redirect, request, session, url_for

NS = {
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
}

SUCCESS = "urn:oasis:names:tc:SAML:2.0:status:Success"


def _local(tag: str) -> str:
    return "{%s}%s" % (NS["saml"], tag)


def _prot(tag: str) -> str:
    return "{%s}%s" % (NS["samlp"], tag)


def _find_status_success(root: ET.Element) -> bool:
    status = root.find(".//%s" % _prot("Status"))
    if status is None:
        return True
    code = status.find("%s" % _prot("StatusCode"))
    if code is None:
        return True
    return code.get("Value") == SUCCESS


def _find_assertions(root: ET.Element) -> list[ET.Element]:
    assertions = root.findall(".//%s" % _local("Assertion"))
    if assertions:
        return assertions
    return [e for e in root.iter() if e.tag.endswith("Assertion")]


def _attribute_values(attr_el: ET.Element) -> list[str]:
    out: list[str] = []
    for av in attr_el.findall("%s" % _local("AttributeValue")):
        if av.text is not None and av.text.strip():
            out.append(av.text.strip())
        elif len(av):
            out.append(ET.tostring(av, encoding="unicode").strip())
    return out


def _extract_attributes(assertion: ET.Element) -> dict[str, list[str]]:
    attrs: dict[str, list[str]] = {}
    for attr in assertion.findall(".//%s" % _local("Attribute")):
        name = attr.get("Name")
        if not name:
            continue
        vals = _attribute_values(attr)
        if vals:
            attrs.setdefault(name, []).extend(vals)
    return attrs


def _subject_name_id(assertion: ET.Element) -> str | None:
    sid = assertion.find(".//%s" % _local("NameID"))
    if sid is not None and sid.text:
        return sid.text.strip()
    return None


def parse_saml_assertion_xml(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    if not _find_status_success(root):
        raise ValueError("SAML status is not Success")
    assertions = _find_assertions(root)
    if not assertions:
        raise ValueError("No SAML Assertion elements in response")
    assertion = assertions[0]
    name_id = _subject_name_id(assertion)
    attributes = _extract_attributes(assertion)
    return {
        "assertion_count": len(assertions),
        "name_id": name_id,
        "attributes": attributes,
        "raw_assertion": ET.tostring(assertion, encoding="unicode"),
    }


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

    @app.route("/")
    def index():
        if session.get("user"):
            return (
                "session: %s"
                % session.get("user", {}).get("name_id", "unknown")
            )
        return "no session; POST SAMLResponse to /acs"

    @app.route("/acs", methods=["POST"])
    def acs():
        saml_b64 = request.form.get("SAMLResponse")
        relay_state = request.form.get("RelayState")
        if not saml_b64:
            return "Missing SAMLResponse", 400
        try:
            xml_bytes = base64.b64decode(saml_b64)
        except Exception:
            return "Invalid SAMLResponse base64", 400
        try:
            parsed = parse_saml_assertion_xml(xml_bytes)
        except ET.ParseError:
            return "Invalid SAML XML", 400
        except ValueError as e:
            return str(e), 400
        user = {
            "name_id": parsed["name_id"],
            "attributes": parsed["attributes"],
            "assertion_count": parsed["assertion_count"],
        }
        session["user"] = user
        session["relay_state"] = relay_state
        session.permanent = True
        next_url = "/"
        if relay_state:
            try:
                p = urlparse(relay_state)
                if p.scheme in ("http", "https") and p.netloc:
                    if p.netloc == request.host:
                        next_url = relay_state
            except Exception:
                pass
        return redirect(next_url)

    @app.route("/logout", methods=["GET", "POST"])
    def logout():
        session.clear()
        return redirect(url_for("index"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))