from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree

from defusedxml import ElementTree as DefusedElementTree
from django.conf import settings


@dataclass
class ParsedAssertion:
    name_id: str
    name_id_format: str | None
    attributes: dict[str, list[str]] = field(default_factory=dict)


class SAMLValidationError(ValueError):
    pass


_NS = {
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
}


def _tag(local: str, ns_uri: str) -> str:
    return f"{{{ns_uri}}}{local}"


def validate_saml_response_structure(root: ElementTree.Element) -> None:
    if root is None:
        raise SAMLValidationError("empty document")
    if root.tag != _tag("Response", _NS["samlp"]):
        raise SAMLValidationError("root element must be samlp:Response")
    status = root.find("samlp:Status", _NS)
    if status is None:
        raise SAMLValidationError("missing samlp:Status")
    sc = status.find("samlp:StatusCode", _NS)
    if sc is None:
        raise SAMLValidationError("missing samlp:StatusCode")
    code = sc.get("Value", "")
    if not code.endswith(":Success"):
        msg_el = status.find("samlp:StatusMessage", _NS)
        msg = msg_el.text if msg_el is not None and msg_el.text else code
        raise SAMLValidationError(f"SAML status not success: {msg}")
    assertions = root.findall("saml:Assertion", _NS)
    if not assertions:
        raise SAMLValidationError("no saml:Assertion elements")
    for assertion in assertions:
        subject = assertion.find("saml:Subject", _NS)
        if subject is None:
            raise SAMLValidationError("assertion missing saml:Subject")
        nameid = subject.find("saml:NameID", _NS)
        if nameid is None or not (nameid.text or "").strip():
            raise SAMLValidationError("missing or empty saml:NameID")


def _collect_attribute_values(attr_el: ElementTree.Element) -> list[str]:
    out: list[str] = []
    for vel in attr_el.findall("saml:AttributeValue", _NS):
        if vel.text and vel.text.strip():
            out.append(vel.text.strip())
        elif list(vel):
            inner = "".join(ElementTree.tostring(c, encoding="unicode") for c in vel)
            if inner.strip():
                out.append(inner.strip())
    return out


def parse_saml_response_xml(xml_bytes: bytes) -> ParsedAssertion:
    try:
        root = DefusedElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as e:
        raise SAMLValidationError(f"invalid XML: {e}") from e
    validate_saml_response_structure(root)
    assertions = root.findall("saml:Assertion", _NS)
    assertion = assertions[0]
    subject = assertion.find("saml:Subject", _NS)
    nameid_el = subject.find("saml:NameID", _NS)
    name_id = (nameid_el.text or "").strip()
    name_id_format = nameid_el.get("Format")
    attrs: dict[str, list[str]] = {}
    for stmt in assertion.findall("saml:AttributeStatement", _NS):
        for attr_el in stmt.findall("saml:Attribute", _NS):
            name = attr_el.get("Name")
            if not name:
                continue
            friendly = attr_el.get("FriendlyName")
            values = _collect_attribute_values(attr_el)
            if not values:
                continue
            attrs.setdefault(name, []).extend(values)
            if friendly:
                attrs.setdefault(friendly, []).extend(values)
    return ParsedAssertion(name_id=name_id, name_id_format=name_id_format, attributes=attrs)


def decode_saml_post_payload(raw_b64: str) -> bytes:
    if not raw_b64 or not raw_b64.strip():
        raise SAMLValidationError("empty SAMLResponse")
    cleaned = re.sub(r"\s+", "", raw_b64.strip())
    pad = (-len(cleaned)) % 4
    if pad:
        cleaned += "=" * pad
    try:
        return base64.b64decode(cleaned, validate=True)
    except (ValueError, binascii.Error) as e:
        raise SAMLValidationError("SAMLResponse is not valid base64") from e


def map_attributes_to_user_fields(parsed: ParsedAssertion) -> dict[str, Any]:
    mapping = getattr(settings, "SAML_ATTRIBUTE_MAP", {})
    user_data: dict[str, Any] = {}
    for attr_name, values in parsed.attributes.items():
        if not values:
            continue
        key = mapping.get(attr_name)
        if not key:
            continue
        val = values[0]
        if key == "email" and val:
            user_data["email"] = val[:254]
        elif key in ("first_name", "last_name") and val:
            user_data[key] = val[:150]
        elif key == "display_name" and val:
            user_data["_display_name"] = val
    return user_data
