import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

portal/__init__.py


portal/asgi.py
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")

application = get_asgi_application()

portal/wsgi.py
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings")

application = get_wsgi_application()

portal/settings.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "change-me-in-production-use-env"

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "saml_sp.apps.SamlSpConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "portal.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "portal.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

SAML_NS = {
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
}

SAML_ATTRIBUTE_MAP = {
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": "email",
    "email": "email",
    "Email": "email",
    "mail": "email",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": "first_name",
    "givenName": "first_name",
    "first_name": "first_name",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": "last_name",
    "sn": "last_name",
    "surname": "last_name",
    "last_name": "last_name",
    "displayName": "display_name",
    "http://schemas.microsoft.com/identity/claims/displayname": "display_name",
}

portal/urls.py
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("saml_sp.urls")),
]

saml_sp/__init__.py


saml_sp/apps.py
from django.apps import AppConfig


class SamlSpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "saml_sp"
    verbose_name = "SAML Service Provider"

saml_sp/saml_parse.py
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

saml_sp/views.py
from __future__ import annotations

import re
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .saml_parse import (
    SAMLValidationError,
    decode_saml_post_payload,
    map_attributes_to_user_fields,
    parse_saml_response_xml,
)

User = get_user_model()


def _safe_relay_url(relay_state: str | None) -> str:
    default = getattr(settings, "LOGIN_REDIRECT_URL", "/")
    if not relay_state:
        return default
    relay_url = relay_state.strip()
    if not relay_url:
        return default
    if relay_url.startswith("/") and not relay_url.startswith("//"):
        return relay_url
    parsed = urlparse(relay_url)
    if parsed.scheme in ("http", "https") and parsed.hostname:
        allowed = {h.lower() for h in getattr(settings, "ALLOWED_HOSTS", []) if h != "*"}
        if parsed.hostname.lower() in allowed:
            return relay_url
    return default


def _username_from_name_id(name_id: str) -> str:
    u = (name_id or "").strip()[:150]
    if not u:
        return "saml_user"
    if re.search(r"[^\w.@+-]", u, re.ASCII):
        u = re.sub(r"[^\w.@+-]", "_", u)[:150] or "saml_user"
    return u


def _apply_or_create_user(parsed) -> User:
    mapped = map_attributes_to_user_fields(parsed)
    email = (mapped.get("email") or "").strip()
    username = _username_from_name_id(parsed.name_id)
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(username=username, email=email or "")
    updates: list[str] = []
    if email and user.email != email:
        user.email = email
        updates.append("email")
    fn = mapped.get("first_name")
    if fn and getattr(user, "first_name", "") != fn:
        user.first_name = fn
        updates.append("first_name")
    ln = mapped.get("last_name")
    if ln and getattr(user, "last_name", "") != ln:
        user.last_name = ln
        updates.append("last_name")
    if updates:
        user.save(update_fields=updates)
    return user


def home(request):
    if request.user.is_authenticated:
        return render(
            request,
            "saml_sp/home.html",
            {"user": request.user},
        )
    return render(request, "saml_sp/login.html")


@csrf_exempt
@require_POST
def assertion_consumer_service(request):
    raw = request.POST.get("SAMLResponse", "")
    relay = request.POST.get("RelayState")
    try:
        xml_bytes = decode_saml_post_payload(raw)
        parsed = parse_saml_response_xml(xml_bytes)
        user = _apply_or_create_user(parsed)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    except SAMLValidationError as e:
        return HttpResponseBadRequest(str(e))
    return HttpResponseRedirect(_safe_relay_url(relay))

saml_sp/urls.py
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("saml/acs/", views.assertion_consumer_service, name="saml_acs"),
]

templates/saml_sp/home.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Portal</title>
</head>
<body>
    <p>Signed in as {{ user.username }} ({{ user.get_full_name|default:user.email }}).</p>
    <p><a href="/admin/">Admin</a></p>
</body>
</html>

templates/saml_sp/login.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Sign in</title>
</head>
<body>
    <p>Use your IdP to POST SAMLResponse to <code>/saml/acs/</code>.</p>
</body>
</html>