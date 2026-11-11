"""Send email through the Gmail API over HTTPS.

Render's free plan blocks SMTP ports, so Gmail's SMTP server cannot be reached. The Gmail API
uses ordinary HTTPS. Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN (from a
Google Cloud OAuth client with the gmail.send scope, authorised as esicomsuppliers@gmail.com).
"""

import base64
import logging
import threading
import time

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105  (a URL, not a secret)
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
_token = {"value": "", "expires": 0.0}
_lock = threading.Lock()


def _access_token(timeout) -> str:
    with _lock:
        if _token["value"] and _token["expires"] > time.time() + 60:
            return _token["value"]
        r = requests.post(
            TOKEN_URL,
            data={
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "refresh_token": settings.GMAIL_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        _token["value"] = data["access_token"]
        _token["expires"] = time.time() + int(data.get("expires_in", 3600))
        return _token["value"]


class GmailApiBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        timeout = getattr(settings, "EMAIL_TIMEOUT", 10) or 10
        sent = 0
        for message in email_messages:
            try:
                token = _access_token(timeout)
                raw = base64.urlsafe_b64encode(message.message().as_bytes()).decode()
                r = requests.post(
                    SEND_URL, json={"raw": raw}, headers={"Authorization": f"Bearer {token}"}, timeout=timeout
                )
                if r.status_code == 401:  # token revoked or expired early: refresh once
                    _token["value"] = ""
                    token = _access_token(timeout)
                    r = requests.post(
                        SEND_URL, json={"raw": raw}, headers={"Authorization": f"Bearer {token}"}, timeout=timeout
                    )
                r.raise_for_status()
                sent += 1
            except Exception:
                logger.exception("Gmail API send failed: %s", message.subject)
                if not self.fail_silently:
                    raise
        return sent
