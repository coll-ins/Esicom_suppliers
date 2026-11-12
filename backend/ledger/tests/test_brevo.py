from unittest import mock

from django.core import mail
from django.test import override_settings


def _ok():
    r = mock.Mock(status_code=201)
    r.raise_for_status.return_value = None
    return r


@override_settings(EMAIL_BACKEND="ledger.brevo_backend.BrevoApiBackend", BREVO_API_KEY="test-key")
def test_brevo_backend_sends_over_https():
    with mock.patch("ledger.brevo_backend.requests.post", return_value=_ok()) as post:
        sent = mail.EmailMessage("Hi", "Body", "Esicom Suppliers <esicomsuppliers@gmail.com>", ["a@example.com"]).send()
    assert sent == 1
    call = post.call_args
    assert call.args[0] == "https://api.brevo.com/v3/smtp/email"
    assert call.kwargs["headers"]["api-key"] == "test-key"
    payload = call.kwargs["json"]
    assert payload["sender"] == {"email": "esicomsuppliers@gmail.com", "name": "Esicom Suppliers"}
    assert payload["to"] == [{"email": "a@example.com"}]
    assert payload["subject"] == "Hi" and payload["textContent"] == "Body"


@override_settings(EMAIL_BACKEND="ledger.brevo_backend.BrevoApiBackend", BREVO_API_KEY="test-key")
def test_brevo_backend_sends_attachment_base64():
    with mock.patch("ledger.brevo_backend.requests.post", return_value=_ok()) as post:
        msg = mail.EmailMessage("Hi", "Body", "esicomsuppliers@gmail.com", ["a@example.com"])
        msg.attach("invoice.pdf", b"%PDF-fake-content", "application/pdf")
        msg.send()
    att = post.call_args.kwargs["json"]["attachment"][0]
    assert att["name"] == "invoice.pdf"
    import base64

    assert base64.b64decode(att["content"]) == b"%PDF-fake-content"
