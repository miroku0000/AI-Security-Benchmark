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
