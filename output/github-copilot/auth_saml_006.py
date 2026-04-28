#!/usr/bin/env python3
import base64
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
import xml.etree.ElementTree as ET

from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "django_saml_sp.sqlite3"

if not settings.configured:
    settings.configure(
        DEBUG=os.environ.get("DJANGO_DEBUG", "").lower() in {"1", "true", "yes"},
        SECRET_KEY=os.environ.get("DJANGO_SECRET_KEY", "change-this-secret-key"),
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(","),
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
        ],
        MIDDLEWARE=[
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
        ],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            }
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": str(DATABASE_PATH),
            }
        },
        SESSION_ENGINE="django.contrib.sessions.backends.db",
        AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
        AUTH_PASSWORD_VALIDATORS=[],
        USE_TZ=True,
        TIME_ZONE="UTC",
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
    )

import django

django.setup()

from django.contrib.auth import get_user_model, login, logout
from django.core.management import call_command, execute_from_command_line
from django.core.wsgi import get_wsgi_application
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

SAML_NS = {
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
}
MAX_SAML_RESPONSE_BYTES = 1024 * 1024


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _reject_unsafe_xml(raw_xml: bytes) -> None:
    if len(raw_xml) > MAX_SAML_RESPONSE_BYTES:
        raise ValueError("SAML response exceeds maximum size")
    lowered = raw_xml.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise ValueError("SAML response contains an unsafe XML declaration")


def _parse_time(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid SAML timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _first_text(node: ET.Element, xpath: str) -> str:
    found = node.find(xpath, SAML_NS)
    if found is None or found.text is None:
        return ""
    return found.text.strip()


def _extract_attribute_values(attribute: ET.Element) -> List[str]:
    values: List[str] = []
    for value_node in attribute.findall("saml:AttributeValue", SAML_NS):
        text = "".join(value_node.itertext()).strip()
        if text:
            values.append(text)
    return values


def _normalize_username(name_id: str) -> str:
    cleaned = name_id.strip()
    if cleaned and len(cleaned) <= 150:
        return cleaned
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    return f"saml-{digest[:145]}"


def _decode_saml_response(encoded_response: str) -> bytes:
    normalized = "".join(encoded_response.split())
    if not normalized:
        raise ValueError("SAMLResponse is required")
    try:
        return base64.b64decode(normalized, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("SAMLResponse is not valid base64") from exc


def _parse_saml_assertion(raw_xml: bytes) -> Tuple[str, Dict[str, Any]]:
    _reject_unsafe_xml(raw_xml)

    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError as exc:
        raise ValueError("SAML response is not valid XML") from exc

    if _local_name(root.tag) != "Response":
        raise ValueError("Root element must be a SAML Response")

    assertion = root.find("saml:Assertion", SAML_NS)
    if assertion is None:
        raise ValueError("SAML Response does not contain an Assertion")

    issuer = _first_text(root, "saml:Issuer") or _first_text(assertion, "saml:Issuer")
    if not issuer:
        raise ValueError("SAML Assertion is missing an Issuer")

    subject = assertion.find("saml:Subject", SAML_NS)
    if subject is None:
        raise ValueError("SAML Assertion is missing a Subject")

    name_id = _first_text(subject, "saml:NameID")
    if not name_id:
        raise ValueError("SAML Assertion is missing a NameID")

    conditions = assertion.find("saml:Conditions", SAML_NS)
    if conditions is not None:
        now = datetime.now(timezone.utc)
        not_before = conditions.get("NotBefore")
        not_on_or_after = conditions.get("NotOnOrAfter")
        if not_before and now < _parse_time(not_before):
            raise ValueError("SAML Assertion is not yet valid")
        if not_on_or_after and now >= _parse_time(not_on_or_after):
            raise ValueError("SAML Assertion has expired")

    attributes: Dict[str, Any] = {}
    attribute_statement = assertion.find("saml:AttributeStatement", SAML_NS)
    if attribute_statement is not None:
        for attribute in attribute_statement.findall("saml:Attribute", SAML_NS):
            name = attribute.get("Name") or attribute.get("FriendlyName")
            if not name:
                continue
            values = _extract_attribute_values(attribute)
            if not values:
                continue
            attributes[name] = values[0] if len(values) == 1 else values

    authn_statement = assertion.find("saml:AuthnStatement", SAML_NS)
    session_index = ""
    if authn_statement is not None:
        session_index = (authn_statement.get("SessionIndex") or "").strip()

    return name_id, {
        "issuer": issuer,
        "attributes": attributes,
        "session_index": session_index,
    }


def _user_defaults_from_attributes(attributes: Dict[str, Any]) -> Dict[str, str]:
    defaults: Dict[str, str] = {}
    email = attributes.get("email") or attributes.get("mail")
    first_name = attributes.get("first_name") or attributes.get("givenName")
    last_name = attributes.get("last_name") or attributes.get("sn")

    if isinstance(email, str) and email:
        defaults["email"] = email
    if isinstance(first_name, str) and first_name:
        defaults["first_name"] = first_name
    if isinstance(last_name, str) and last_name:
        defaults["last_name"] = last_name
    return defaults


def _sign_in_user(request: HttpRequest, name_id: str, attributes: Dict[str, Any]) -> Any:
    user_model = get_user_model()
    username = _normalize_username(name_id)
    defaults = _user_defaults_from_attributes(attributes)

    user, created = user_model.objects.get_or_create(username=username, defaults=defaults)

    updated_fields = set()
    for field_name, field_value in defaults.items():
        if getattr(user, field_name, "") != field_value:
            setattr(user, field_name, field_value)
            updated_fields.add(field_name)

    if created:
        user.set_unusable_password()
        updated_fields.add("password")

    if updated_fields:
        user.save(update_fields=sorted(updated_fields))

    user.backend = "django.contrib.auth.backends.ModelBackend"
    login(request, user)
    request.session["saml_name_id"] = name_id
    request.session["saml_attributes"] = attributes
    return user


def index(_request: HttpRequest) -> HttpResponse:
    return HttpResponse(
        "<html><body><form method='post' action='/saml/acs/'>"
        "<textarea name='SAMLResponse' rows='20' cols='120'></textarea>"
        "<br><button type='submit'>Submit SAMLResponse</button>"
        "</form></body></html>"
    )


@csrf_exempt
def saml_acs(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST is supported")

    try:
        xml_bytes = _decode_saml_response(request.POST.get("SAMLResponse", ""))
        name_id, saml_data = _parse_saml_assertion(xml_bytes)
        user = _sign_in_user(request, name_id, saml_data["attributes"])
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(
        {
            "authenticated": True,
            "username": user.get_username(),
            "name_id": name_id,
            "attributes": saml_data["attributes"],
            "issuer": saml_data["issuer"],
            "session_index": saml_data["session_index"],
            "session_key": request.session.session_key,
        }
    )


def current_user(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=401)

    return JsonResponse(
        {
            "authenticated": True,
            "username": request.user.get_username(),
            "name_id": request.session.get("saml_name_id", ""),
            "attributes": request.session.get("saml_attributes", {}),
        }
    )


@csrf_exempt
def saml_logout(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST is supported")
    logout(request)
    return JsonResponse({"authenticated": False})


urlpatterns = [
    path("", index),
    path("saml/acs/", saml_acs),
    path("me/", current_user),
    path("logout/", saml_logout),
]

application = get_wsgi_application()


def _prepare_database() -> None:
    call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.extend(["runserver", "0.0.0.0:8000", "--noreload"])
    if sys.argv[1] == "runserver" and os.environ.get("RUN_MAIN") != "true":
        _prepare_database()
    execute_from_command_line(sys.argv)