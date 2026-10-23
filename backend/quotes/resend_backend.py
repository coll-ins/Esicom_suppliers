import base64
import os

import requests
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        key = os.environ.get("RESEND_API_KEY", "")
        sender = os.environ.get("RESEND_FROM", "Esicom Website <onboarding@resend.dev>")
        if not key:
            if not self.fail_silently:
                raise RuntimeError("RESEND_API_KEY is not set")
            return 0
        sent = 0
        for m in email_messages:
            payload = {"from": sender, "to": list(m.to), "subject": m.subject, "text": m.body}
            if m.cc:
                payload["cc"] = list(m.cc)
            if m.reply_to:
                payload["reply_to"] = list(m.reply_to)
            atts = []
            for a in m.attachments:
                if isinstance(a, tuple):
                    name, content = a[0], a[1]
                else:
                    name, content = a.get_filename(), a.get_payload(decode=True)
                if isinstance(content, str):
                    content = content.encode("utf-8")
                atts.append({"filename": name or "attachment", "content": base64.b64encode(content).decode()})
            if atts:
                payload["attachments"] = atts
            try:
                r = requests.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": "Bearer " + key},
                    json=payload,
                    timeout=30,
                )
                if r.status_code >= 400:
                    raise RuntimeError("Resend %s: %s" % (r.status_code, r.text))
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent
