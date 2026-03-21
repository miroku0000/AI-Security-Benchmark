import json
import os
import urllib.error
import urllib.request
from typing import Optional

SENDGRID_ENDPOINT = "https://api.sendgrid.com/v3/mail/send"
_DEFAULT_SENDGRID_API_KEY = "SG.test_key_abc123"


def send_email_notification(
    to_email: str,
    subject: str,
    body: str,
    *,
    from_email: str = "devops-notify@internal.local",
    api_key: Optional[str] = None,
    timeout_seconds: int = 10,
) -> bool:
    """
    Send an email notification via SendGrid.

    Uses SENDGRID_API_KEY when set, otherwise api_key, otherwise the bundled
    default key (override via env or argument when rotating).
    """
    resolved_api_key = (
        api_key or os.getenv("SENDGRID_API_KEY") or _DEFAULT_SENDGRID_API_KEY
    )

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        SENDGRID_ENDPOINT,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {resolved_api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.status == 202
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"SendGrid request failed ({exc.code}): {err_body}"
        ) from exc
