import base64
import zlib
from xml.etree import ElementTree as ET

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.views import View

# SAML namespace constants
SAML_NAMESPACES = {
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}

SAML_SUCCESS_STATUS = "urn:oasis:names:tc:SAML:2.0:status:Success"


class SAMLResponseView(View):
    """Handle SAML POST responses from an Identity Provider."""

    def post(self, request):
        raw_response = request.POST.get("SAMLResponse")
        if not raw_response:
            return HttpResponseBadRequest("Missing SAMLResponse parameter")

        try:
            xml_bytes = base64.b64decode(raw_response)
        except Exception:
            return HttpResponseBadRequest("Invalid base64 encoding")

        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError:
            return HttpResponseBadRequest("Invalid XML in SAML response")

        validation_error = self._validate_response(root)
        if validation_error:
            return HttpResponseBadRequest(validation_error)

        name_id = self._extract_name_id(root)
        if not name_id:
            return HttpResponseBadRequest("Missing NameID in SAML assertion")

        attributes = self._extract_attributes(root)

        user = self._get_or_create_user(name_id, attributes)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        relay_state = request.POST.get("RelayState", "/")
        return HttpResponseRedirect(relay_state)

    def _validate_response(self, root):
        if root.tag != f"{{{SAML_NAMESPACES['samlp']}}}Response":
            return "Root element is not a SAML Response"

        status_el = root.find("samlp:Status/samlp:StatusCode", SAML_NAMESPACES)
        if status_el is None:
            return "Missing Status element"

        status_value = status_el.get("Value", "")
        if status_value != SAML_SUCCESS_STATUS:
            return f"SAML authentication failed: {status_value}"

        assertion = root.find("saml:Assertion", SAML_NAMESPACES)
        if assertion is None:
            return "Missing Assertion element"

        issuer = root.find("saml:Issuer", SAML_NAMESPACES)
        if issuer is None or not issuer.text:
            return "Missing Issuer element"

        expected_issuer = getattr(settings, "SAML_IDP_ENTITY_ID", None)
        if expected_issuer and issuer.text.strip() != expected_issuer:
            return "Issuer mismatch"

        expected_audience = getattr(settings, "SAML_SP_ENTITY_ID", None)
        if expected_audience:
            audience_el = assertion.find(
                "saml:Conditions/saml:AudienceRestriction/saml:Audience",
                SAML_NAMESPACES,
            )
            if audience_el is not None and audience_el.text:
                if audience_el.text.strip() != expected_audience:
                    return "Audience mismatch"

        return None

    def _extract_name_id(self, root):
        assertion = root.find("saml:Assertion", SAML_NAMESPACES)
        if assertion is None:
            return None
        subject = assertion.find("saml:Subject/saml:NameID", SAML_NAMESPACES)
        if subject is not None and subject.text:
            return subject.text.strip()
        return None

    def _extract_attributes(self, root):
        attributes = {}
        assertion = root.find("saml:Assertion", SAML_NAMESPACES)
        if assertion is None:
            return attributes

        attr_statement = assertion.find("saml:AttributeStatement", SAML_NAMESPACES)
        if attr_statement is None:
            return attributes

        for attr_el in attr_statement.findall("saml:Attribute", SAML_NAMESPACES):
            attr_name = attr_el.get("Name", "")
            if not attr_name:
                continue
            values = []
            for val_el in attr_el.findall("saml:AttributeValue", SAML_NAMESPACES):
                if val_el.text:
                    values.append(val_el.text.strip())
            if len(values) == 1:
                attributes[attr_name] = values[0]
            elif values:
                attributes[attr_name] = values
        return attributes

    def _get_or_create_user(self, name_id, attributes):
        email = attributes.get("email", attributes.get("mail", name_id))
        first_name = attributes.get("firstName", attributes.get("givenName", ""))
        last_name = attributes.get("lastName", attributes.get("sn", ""))

        try:
            user = User.objects.get(username=name_id)
            user.email = email
            user.first_name = first_name[:30] if first_name else ""
            user.last_name = last_name[:150] if last_name else ""
            user.save(update_fields=["email", "first_name", "last_name"])
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=name_id,
                email=email,
                first_name=first_name[:30] if first_name else "",
                last_name=last_name[:150] if last_name else "",
            )
        return user