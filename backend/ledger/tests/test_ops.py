from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import override_settings

from ledger import gmail_backend, services
from ledger.models import Document

from .conftest import item


@pytest.mark.django_db(databases=["default", "neon"], transaction=True)
def test_move_database_copies_everything_once(owner, customer, paper, capsys):
    services.record_sale(owner, customer, [item(paper, 2)], payment={"amount": 1508, "method": "cash"})
    call_command("move_database")
    assert "copied" in capsys.readouterr().out
    assert Document.objects.using("neon").count() == Document.objects.count() == 1
    assert get_user_model().objects.using("neon").get(email=owner.email).check_password  # same user rows
    call_command("move_database")
    assert "already has data" in capsys.readouterr().out
    assert Document.objects.using("neon").count() == 1


def _ok(payload):
    r = mock.Mock(status_code=200)
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


@override_settings(
    EMAIL_BACKEND="ledger.gmail_backend.GmailApiBackend",
    GMAIL_CLIENT_ID="id",
    GMAIL_CLIENT_SECRET="secret",
    GMAIL_REFRESH_TOKEN="refresh",
)
def test_gmail_backend_sends_over_https():
    gmail_backend._token["value"] = ""
    with mock.patch("ledger.gmail_backend.requests.post") as post:
        post.side_effect = [_ok({"access_token": "tok", "expires_in": 3600}), _ok({"id": "1"})]
        sent = mail.EmailMessage("Hi", "Body", "esicomsuppliers@gmail.com", ["a@example.com"]).send()
    assert sent == 1
    token_call, send_call = post.call_args_list
    assert token_call.args[0] == gmail_backend.TOKEN_URL and token_call.kwargs["data"]["grant_type"] == "refresh_token"
    assert send_call.kwargs["headers"]["Authorization"] == "Bearer tok"
    assert "raw" in send_call.kwargs["json"]
