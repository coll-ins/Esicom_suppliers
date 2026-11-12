"""Send email through Brevo's transactional email API over HTTPS.

Render's free plan blocks SMTP ports, so Brevo's SMTP relay cannot be reached either;
this uses Brevo's HTTPS API instead. Set BREVO_API_KEY (Brevo: SMTP & API -> API Keys).
The sender address must be a "verified sender" in Brevo (a one-click email confirmation,
no domain needed).
"""

import base64
import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)
SEND_URL = "https://api.brevo.com/v3/smtp/email"


def _split_from(from_email: str) -> tuple[str, str]:
    """ "Esicom Suppliers <esicomsuppliers@gmail.com>" -> ("Esicom Suppliers", "esicomsuppliers@gmail.com")."""
    if "<" in from_email and from_email.endswith(">"):
        name, addr = from_email.rsplit("<", 1)
        return name.strip(), addr[:-1].strip()
    return "", from_email.strip()


class BrevoApiBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        timeout = getattr(settings, "EMAIL_TIMEOUT", 10) or 10
        sent = 0
        for message in email_messages:
            name, addr = _split_from(message.from_email or settings.DEFAULT_FROM_EMAIL)
            payload = {
                "sender": {"email": addr, **({"name": name} if name else {})},
                "to": [{"email": e} for e in message.to],
                "subject": message.subject,
                "textContent": message.body,
            }
            if message.cc:
                payload["cc"] = [{"email": e} for e in message.cc]
            if message.reply_to:
                payload["replyTo"] = {"email": message.reply_to[0]}
            attachments = [
                {
                    "name": filename,
                    "content": base64.b64encode(content.encode() if isinstance(content, str) else content).decode(),
                }
                for filename, content, _mimetype in message.attachments
                if isinstance(filename, str)
            ]
            if attachments:
                payload["attachment"] = attachments
            try:
                r = requests.post(
                    SEND_URL,
                    json=payload,
                    headers={"api-key": settings.BREVO_API_KEY, "Accept": "application/json"},
                    timeout=timeout,
                )
                r.raise_for_status()
                sent += 1
            except Exception:
                logger.exception("Brevo API send failed: %s", message.subject)
                if not self.fail_silently:
                    raise
        return sent
