import re
from io import BytesIO

import pytest
from django.core import mail
from django.test import Client
from django.urls import get_resolver
from pypdf import PdfReader

from ledger import services
from ledger.models import Customer, LoginAttempt

from .conftest import PASSWORD, item, logged_in

pytestmark = pytest.mark.django_db
PUBLIC = {"auth/csrf/", "auth/login/", "auth/reset/request/", "auth/reset/confirm/"}


def ledger_paths():
    resolver = get_resolver()
    for pattern in resolver.url_patterns:
        if str(pattern.pattern) == "api/ledger/":
            for sub in pattern.url_patterns:
                yield re.sub(r"<int:\w+>", "1", re.sub(r"<str:\w+>", "original", str(sub.pattern)))


def post(client, url, data=None):
    return client.post(url, data or {}, content_type="application/json")


def test_every_ledger_endpoint_requires_login():
    c = Client()
    paths = list(ledger_paths())
    assert len(paths) > 40
    for p in paths:
        if p in PUBLIC:
            continue
        for method in ("get", "post"):
            r = getattr(c, method)(f"/api/ledger/{p}", content_type="application/json")
            assert r.status_code in (401, 403, 405), (p, method, r.status_code)
            assert r.status_code != 200


def test_staff_cannot_reach_owner_endpoints(staff_client):
    for p in ("users/", "settings/", "audit/", "reports/profit/"):
        assert staff_client.get(f"/api/ledger/{p}").status_code == 403, p


def test_staff_never_sees_cost(owner, staff_client, paper):
    r = staff_client.get("/api/ledger/products/")
    assert "cost_price" not in r.json()[0]
    detail = staff_client.get(f"/api/ledger/products/{paper.pk}/").json()
    assert "cost_price" not in detail and all("unit_cost" not in m for m in detail["movements"])
    r = post(staff_client, "/api/ledger/products/", {"name": "Pens", "price": 20, "cost_price": 10})
    assert r.status_code == 400 and "owner" in r.json()["detail"]
    r = staff_client.get("/api/ledger/reports/money/")
    assert "stock_bought" not in r.json()


def test_owner_sees_cost(owner_client, paper):
    assert owner_client.get("/api/ledger/products/").json()[0]["cost_price"] == 500


def test_staff_vat_exempt_needs_owner_permission(staff_client, paper, owner_client):
    r = staff_client.patch(f"/api/ledger/products/{paper.pk}/", {"vat_exempt": True}, content_type="application/json")
    assert r.status_code == 400
    owner_client.put("/api/ledger/settings/", {"staff_can_set_vat_exempt": True}, content_type="application/json")
    r = staff_client.patch(f"/api/ledger/products/{paper.pk}/", {"vat_exempt": True}, content_type="application/json")
    assert r.status_code == 200 and r.json()["vat_exempt"] is True


def test_staff_cannot_void(staff_client, owner, customer, paper):
    inv = services.record_sale(owner, customer, [item(paper, 1)]).invoice
    r = post(staff_client, f"/api/ledger/documents/{inv.pk}/void/", {"reason": "nope"})
    assert r.status_code == 400 and "Only the owner" in r.json()["detail"]


def test_login_lockout_after_five_failures(owner):
    c = Client()
    for _ in range(5):
        r = post(c, "/api/ledger/auth/login/", {"email": owner.email, "password": "wrong"})
        assert r.status_code == 400
    assert "locked" in r.json()["detail"]
    r = post(c, "/api/ledger/auth/login/", {"email": owner.email, "password": PASSWORD})
    assert r.status_code == 429  # even the right password waits 15 minutes
    LoginAttempt.objects.update(locked_until=None, failures=0)
    assert post(c, "/api/ledger/auth/login/", {"email": owner.email, "password": PASSWORD}).status_code == 200


def test_lockout_also_applies_to_unknown_emails():
    c = Client()
    for _ in range(5):
        post(c, "/api/ledger/auth/login/", {"email": "nobody@example.com", "password": "x"})
    r = post(c, "/api/ledger/auth/login/", {"email": "nobody@example.com", "password": "x"})
    assert r.status_code == 429


def test_password_reset_by_email_code(owner):
    c = Client()
    r = post(c, "/api/ledger/auth/reset/request/", {"email": owner.email})
    assert r.status_code == 200
    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
    r = post(
        c,
        "/api/ledger/auth/reset/confirm/",
        {"email": owner.email, "code": "000000" if code != "000000" else "111111", "password": "New-Password-123!"},
    )
    assert r.status_code == 400
    r = post(
        c, "/api/ledger/auth/reset/confirm/", {"email": owner.email, "code": code, "password": "New-Password-123!"}
    )
    assert r.status_code == 200
    assert (
        post(
            c, "/api/ledger/auth/reset/confirm/", {"email": owner.email, "code": code, "password": "Other-Pass-456!"}
        ).status_code
        == 400
    )
    assert (
        post(c, "/api/ledger/auth/login/", {"email": owner.email, "password": "New-Password-123!"}).status_code == 200
    )


def test_reset_request_does_not_reveal_accounts():
    r = post(Client(), "/api/ledger/auth/reset/request/", {"email": "nobody@example.com"})
    assert r.status_code == 200 and len(mail.outbox) == 0


def test_log_out_everywhere(owner):
    phone, laptop = logged_in(owner), logged_in(owner)
    assert laptop.get("/api/ledger/auth/me/").status_code == 200
    assert post(phone, "/api/ledger/auth/logout-all/").status_code == 200
    assert laptop.get("/api/ledger/auth/me/").status_code == 403
    assert logged_in(owner).get("/api/ledger/auth/me/").status_code == 200


def test_removed_staff_is_logged_out(owner_client, staff, staff_client):
    assert post(owner_client, f"/api/ledger/users/{staff.pk}/remove/").status_code == 200
    assert staff_client.get("/api/ledger/home/").status_code == 403


def test_owner_adds_staff(owner_client):
    r = post(
        owner_client, "/api/ledger/users/", {"name": "Jane Wanjiku", "email": "jane@example.com", "password": "short"}
    )
    assert r.status_code == 400
    r = post(
        owner_client,
        "/api/ledger/users/",
        {"name": "Jane Wanjiku", "email": "jane@example.com", "password": "Jane-Starting-Pass-1"},
    )
    assert r.status_code == 201 and r.json()["role"] == "staff"
    c = Client()
    r = post(c, "/api/ledger/auth/login/", {"email": "jane@example.com", "password": "Jane-Starting-Pass-1"})
    assert r.status_code == 200 and c.get("/api/ledger/reports/profit/").status_code == 403


def test_csrf_is_enforced_for_logged_in_requests(owner):
    c = Client(enforce_csrf_checks=True)
    c.get("/api/ledger/auth/csrf/")
    token = c.cookies["csrftoken"].value
    r = c.post(
        "/api/ledger/auth/login/",
        {"email": owner.email, "password": PASSWORD},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert r.status_code == 200
    r = c.post("/api/ledger/customers/", {"name": "No Token"}, content_type="application/json")
    assert r.status_code == 403
    r = c.post(
        "/api/ledger/customers/",
        {"name": "With Token"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=c.cookies["csrftoken"].value,
    )
    assert r.status_code == 201


def test_login_without_csrf_token_is_rejected(owner):
    c = Client(enforce_csrf_checks=True)
    r = c.post("/api/ledger/auth/login/", {"email": owner.email, "password": PASSWORD}, content_type="application/json")
    assert r.status_code == 403


# ---------- validation ----------


@pytest.mark.parametrize(
    "phone,ok",
    [
        ("0712345678", True),
        ("0112 345 678", True),
        ("+254712345678", True),
        ("254712345678", True),
        ("0812345678", False),
        ("071234567", False),
        ("+255712345678", False),
        ("hello", False),
    ],
)
def test_customer_phone_validation(owner_client, phone, ok):
    r = post(owner_client, "/api/ledger/customers/", {"name": "Test Co", "phone": phone})
    assert (r.status_code == 201) is ok, r.content
    if not ok:
        assert "07, 01 or +254" in r.json()["detail"]


@pytest.mark.parametrize("name", ["", "a", "!!!", "x" * 161])
def test_customer_name_rejects_gibberish(owner_client, name):
    assert post(owner_client, "/api/ledger/customers/", {"name": name}).status_code == 400


def test_money_must_be_whole_shillings(owner_client):
    r = post(owner_client, "/api/ledger/products/", {"name": "Pens", "price": "20.50"})
    assert r.status_code == 400 and "No cents" in r.json()["detail"]
    r = post(owner_client, "/api/ledger/products/", {"name": "Pens", "price": "1,500", "opening_qty": 3})
    assert r.status_code == 201 and r.json()["price"] == 1500 and r.json()["on_hand"] == 3


def test_stock_cannot_be_edited_directly(owner_client, paper):
    r = owner_client.patch(f"/api/ledger/products/{paper.pk}/", {"on_hand": 999}, content_type="application/json")
    assert r.status_code == 400 and "Receive or Take out" in r.json()["detail"]


def test_issued_documents_cannot_be_edited(owner_client, owner, customer, paper):
    inv = services.record_sale(owner, customer, [item(paper, 1)]).invoice
    r = owner_client.patch(f"/api/ledger/documents/{inv.pk}/update/", {"total": 1}, content_type="application/json")
    assert r.status_code == 400
    r = owner_client.patch(
        f"/api/ledger/documents/{inv.pk}/update/", {"etims_number": "KRA123"}, content_type="application/json"
    )
    assert r.status_code == 200 and r.json()["etims_number"] == "KRA123"


# ---------- flows ----------


def test_cash_sale_with_receipt_over_api(staff_client, paper):
    r = post(
        staff_client,
        "/api/ledger/sales/",
        {
            "walk_in": True,
            "items": [{"product_id": paper.pk, "qty": 2}, {"description": "Lamination", "qty": 2, "unit_price": 50}],
            "paid_now": {"amount": 1700, "method": "mpesa", "reference": "tkb7xy12ab"},
            "receipt": True,
        },
    )
    assert r.status_code == 201, r.content
    data = r.json()
    # paper 1300 + VAT 208, lamination 100 + VAT 16
    assert data["invoice"]["total"] == 1624 and data["invoice"]["status"] == "paid"
    assert data["overpaid"] == 76 and data["receipt"]["total"] == 1624
    pdf = staff_client.get(f"/api/ledger/documents/{data['receipt']['id']}/pdf/")
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
    assert "RECEIPT" in text and "1,624" in text and "TKB7XY12AB" in text


def test_sale_blocked_over_stock_over_api(staff_client, customer, paper):
    r = post(
        staff_client, "/api/ledger/sales/", {"customer_id": customer.pk, "items": [{"product_id": paper.pk, "qty": 21}]}
    )
    assert r.status_code == 400 and "only 20 left" in r.json()["detail"]


def test_sale_with_new_customer_rolls_back_on_error(staff_client, paper):
    r = post(
        staff_client,
        "/api/ledger/sales/",
        {"new_customer": {"name": "Fresh Co", "phone": "0712345678"}, "items": [{"product_id": paper.pk, "qty": 99}]},
    )
    assert r.status_code == 400
    assert not Customer.objects.filter(name="Fresh Co").exists()


def test_invoice_pdf_total_matches(owner_client, owner, customer, paper):
    inv = services.record_sale(owner, customer, [item(paper, 3)]).invoice
    r = owner_client.get(f"/api/ledger/documents/{inv.pk}/pdf/")
    assert r["Content-Type"] == "application/pdf"
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(r.content)).pages)
    assert inv.number in text and f"{inv.total:,}" in text


def test_statement_pdf_and_email(owner_client, owner, customer, paper):
    services.record_sale(owner, customer, [item(paper, 1)])
    r = post(owner_client, f"/api/ledger/customers/{customer.pk}/statement/", {})
    assert r["Content-Type"] == "application/pdf"
    assert "754" in "\n".join(p.extract_text() for p in PdfReader(BytesIO(r.content)).pages)
    r = post(owner_client, f"/api/ledger/customers/{customer.pk}/statement/", {"email": True})
    assert r.status_code == 200 and mail.outbox[-1].to == [customer.email]


def test_documents_filter_by_status(owner_client, owner, customer, paper):
    a = services.record_sale(owner, customer, [item(paper, 1)]).invoice
    services.record_sale(owner, customer, [item(paper, 1)], payment={"amount": 754, "method": "cash"})
    unpaid = owner_client.get("/api/ledger/documents/?type=INV&status=unpaid").json()
    assert [d["id"] for d in unpaid] == [a.pk]
    assert len(owner_client.get("/api/ledger/documents/?type=INV&status=paid").json()) == 1


def test_reports_respond(owner_client, owner, customer, paper):
    services.record_sale(owner, customer, [item(paper, 2)], payment={"amount": 1508, "method": "cash"})
    for p in (
        "home/",
        "reports/money/",
        "reports/aging/",
        "reports/sales/",
        "reports/profit/",
        "reports/vat/",
        "buy-list/",
    ):
        assert owner_client.get(f"/api/ledger/{p}").status_code == 200, p
    profit = owner_client.get("/api/ledger/reports/profit/").json()
    assert profit["sales_ex_vat"] == 1300 and profit["cost"] == 1000 and profit["profit"] == 300
    vat = owner_client.get("/api/ledger/reports/vat/").json()
    assert sum(m["vat"] for m in vat["months"]) == 208
    home = owner_client.get("/api/ledger/home/").json()
    assert home["cash_collected"] == 1508 and home["invoiced"] == 1508


def test_qr_code_is_staff_only_png(staff_client):
    r = staff_client.get("/api/ledger/qr.png")
    assert r.status_code == 200 and r["Content-Type"] == "image/png"
    assert r["X-Upload-Url"].endswith("/upload/")
    assert Client().get("/api/ledger/qr.png").status_code == 403


def test_audit_log_records_actions(owner_client, owner, customer, paper):
    services.record_sale(owner, customer, [item(paper, 1)])
    entries = owner_client.get("/api/ledger/audit/").json()
    assert any("Issued ESI-INV" in e["summary"] for e in entries)
    assert any(e["action"] == "login" for e in entries)
