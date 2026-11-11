"""Dashboard API under /api/ledger/. Every endpoint needs a logged-in owner or staff user,
except login, CSRF and password reset."""

import logging
from datetime import date, timedelta
from functools import wraps
from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, logout
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.authentication import CSRFCheck
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from quotes.models import FileSubmission, QuoteRequest

from . import auth, emails, pdf, services
from .auth import IsLedgerUser, IsOwner, is_owner
from .models import (
    Alert,
    AuditLog,
    BusinessSettings,
    Customer,
    DocType,
    Document,
    Payment,
    Product,
    Profile,
    Role,
    SaleLine,
    StockMovement,
)
from .services import Item, LedgerError
from .validators import (
    clean_text,
    display_ke_phone,
    normalize_ke_phone,
    whole_kes,
    whole_qty,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------- helpers ----------


def handles_errors(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        try:
            return fn(request, *args, **kwargs)
        except (LedgerError, ValueError) as e:
            return Response({"detail": str(e)}, status=400)

    return wrapper


def ledger_view(methods, owner_only=False):
    """api_view + login required (+ owner) + plain-English errors."""

    def deco(fn):
        fn = handles_errors(fn)
        fn = permission_classes([IsOwner] if owner_only else [IsLedgerUser])(fn)
        fn = authentication_classes([auth.LedgerSessionAuthentication])(fn)
        return api_view(methods)(fn)

    return deco


def enforce_csrf(request) -> str | None:
    """DRF marks API views csrf_exempt and only checks CSRF for logged-in users,
    so login and password reset run the same check here (stops login CSRF)."""
    check = CSRFCheck(lambda r: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    return reason or None  # DRF's CSRFCheck returns the reason as text


def public_view(methods):
    def deco(fn):
        inner = handles_errors(fn)

        @wraps(fn)
        def guarded(request, *args, **kwargs):
            if enforce_csrf(request._request):
                return Response({"detail": "Your session expired. Refresh the page and try again."}, status=403)
            return inner(request, *args, **kwargs)

        guarded = permission_classes([AllowAny])(guarded)
        guarded = authentication_classes([])(guarded)
        return api_view(methods)(guarded)

    return deco


def body(request) -> dict:
    data = request.data
    if not isinstance(data, dict):
        raise ValueError("Send the form fields as JSON.")
    return data


def parse_date(raw, field: str, *, required=False):
    if raw in (None, ""):
        if required:
            raise ValueError(f"{field} is required. Use the format YYYY-MM-DD, for example 2026-11-30.")
        return None
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        raise ValueError(f"{field} must be a date like 2026-11-30.") from None


def period(request, default_days=30):
    end = parse_date(request.query_params.get("to"), "To date") or services.today()
    start = parse_date(request.query_params.get("from"), "From date") or end - timedelta(days=default_days - 1)
    if start > end:
        raise ValueError("The From date must be on or before the To date.")
    return start, end


def flag(raw) -> bool:
    return raw in (True, "true", "1", 1, "on", "yes")


def pdf_response(content: bytes, filename: str, inline=True) -> HttpResponse:
    resp = HttpResponse(content, content_type="application/pdf")
    resp["Content-Disposition"] = f'{"inline" if inline else "attachment"}; filename="{filename}"'
    resp["Cache-Control"] = "private, no-store"
    return resp


# ---------- serializers (plain dicts; cost and profit only for the owner) ----------


def user_json(u):
    return {
        "id": u.pk,
        "name": u.get_full_name() or u.email,
        "email": u.email,
        "role": u.ledger_profile.role,
        "active": u.is_active,
    }


def customer_json(c, with_balance=True, balance=None):
    data = {
        "id": c.pk,
        "name": c.name,
        "phone": display_ke_phone(c.phone),
        "email": c.email,
        "address": c.address,
        "kra_pin": c.kra_pin,
        "billing": c.billing,
        "allow_partial": c.allow_partial,
        "credit_limit": c.credit_limit,
        "payment_terms_days": c.payment_terms_days,
        "is_walk_in": c.is_walk_in,
        "active": c.active,
    }
    if balance is not None:
        data["balance"] = balance
    elif with_balance:
        data["balance"] = services.customer_balance(c)
    return data


def product_json(p, on_hand: int, owner: bool):
    status = "out" if on_hand <= 0 else ("reorder" if on_hand <= p.reorder_level else "ok")
    data = {
        "id": p.pk,
        "name": p.name,
        "unit": p.unit,
        "price": p.price,
        "vat_exempt": p.vat_exempt,
        "reorder_level": p.reorder_level,
        "active": p.active,
        "on_hand": on_hand,
        "status": status,
    }
    if owner:
        data["cost_price"] = p.cost_price
    return data


def doc_status(d) -> str:
    if d.void:
        return "void"
    if d.doc_type != DocType.INVOICE:
        return "issued"
    bal = d.bal if hasattr(d, "bal") else d.balance()
    if bal <= 0:
        return "paid"
    if d.due_on and d.due_on < services.today():
        return "overdue"
    return "unpaid"


def document_json(d, detail=False):
    data = {
        "id": d.pk,
        "type": d.doc_type,
        "type_label": d.get_doc_type_display(),
        "number": d.number,
        "customer": {"id": d.customer_id, "name": d.customer.name},
        "issued_on": d.issued_on,
        "due_on": d.due_on,
        "subtotal": d.subtotal,
        "vat": d.vat,
        "total": d.total,
        "status": doc_status(d),
        "void": d.void,
        "etims_number": d.etims_number,
    }
    if d.doc_type == DocType.INVOICE:
        data["balance"] = d.bal if hasattr(d, "bal") else d.balance()
    if detail:
        data.update(
            {
                "lines": [
                    {
                        "description": ln.description,
                        "qty": ln.qty,
                        "unit_price": ln.unit_price,
                        "vat_exempt": ln.vat_exempt,
                        "amount": ln.amount,
                        "vat": ln.vat,
                        "product_id": ln.product_id,
                        "restock": ln.restock,
                    }
                    for ln in d.lines.all()
                ],
                "vat_percent": d.vat_percent,
                "void_reason": d.void_reason,
                "notes": d.notes,
                "related": {"id": d.related_id, "number": d.related.number} if d.related_id else None,
                "children": [
                    {"id": c.pk, "number": c.number, "type": c.doc_type, "void": c.void} for c in d.children.all()
                ],
                "payments": [
                    {
                        "id": a.payment_id,
                        "amount": a.amount,
                        "method": a.payment.get_method_display(),
                        "reference": a.payment.reference,
                        "received_on": a.payment.received_on,
                    }
                    for a in d.allocations.select_related("payment")
                ],
                "allow_partial": d.allow_partial,
                "partial_allowed": d.partial_allowed(),
                "customer_phone": display_ke_phone(d.customer.phone),
                "customer_email": d.customer.email,
                "whatsapp": {"phone": emails.whatsapp_phone(d.customer), "text": emails.whatsapp_text(d)},
            }
        )
    return data


def payment_json(p):
    return {
        "id": p.pk,
        "customer": {"id": p.customer_id, "name": p.customer.name},
        "amount": p.amount,
        "method": p.method,
        "method_label": p.get_method_display(),
        "reference": p.reference,
        "received_on": p.received_on,
        "refunded": p.refunded,
        "unallocated": p.unallocated(),
        "void": p.void,
        "allocations": [
            {"invoice_id": a.invoice_id, "number": a.invoice.number, "amount": a.amount}
            for a in p.allocations.select_related("invoice")
        ],
        "receipt": next(({"id": r.pk, "number": r.number} for r in p.receipts.all() if not r.void), None),
    }


# ---------- input parsing ----------


def parse_customer_fields(data, *, partial=False, owner=False) -> dict:
    out = {}
    if not partial or "name" in data:
        out["name"] = clean_text(data.get("name"), "Customer name", min_len=2, max_len=160)
    if "phone" in data:
        out["phone"] = normalize_ke_phone(data["phone"]) if str(data["phone"] or "").strip() else ""
    if "email" in data:
        email = str(data.get("email") or "").strip()
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise ValueError("Email must look like name@example.com.") from None
        out["email"] = email
    for key, label, n in (("address", "Address", 200), ("kra_pin", "KRA PIN", 20)):
        if key in data:
            out[key] = clean_text(data.get(key), label, max_len=n)
    if "billing" in data:
        if data["billing"] not in Customer.Billing.values:
            raise ValueError("Billing must be 'One invoice per sale' or 'Running tab'.")
        out["billing"] = data["billing"]
    owner_fields = {"allow_partial", "credit_limit", "payment_terms_days"}
    if owner_fields & set(data) and not owner:
        raise ValueError("Only the owner can change part payments, credit limit or payment terms.")
    if "allow_partial" in data:
        out["allow_partial"] = flag(data["allow_partial"])
    if "credit_limit" in data:
        raw = data["credit_limit"]
        out["credit_limit"] = None if raw in (None, "") else whole_kes(raw, "Credit limit")
    if "payment_terms_days" in data:
        raw = data["payment_terms_days"]
        out["payment_terms_days"] = (
            None if raw in (None, "") else whole_qty(raw, "Payment terms (days)", minimum=0, maximum=365)
        )
    if "active" in data:
        out["active"] = flag(data["active"])
    return out


def parse_items(raw_items, *, allow_restock=False) -> list[Item]:
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("Add at least one item.")
    if len(raw_items) > 200:
        raise ValueError("A document can have at most 200 lines.")
    items = []
    for n, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Line {n} is not valid.")
        qty = whole_qty(raw.get("qty"), f"Line {n} quantity")
        if raw.get("product_id"):
            product = Product.objects.filter(pk=raw["product_id"], active=True).first()
            if not product:
                raise ValueError(f"Line {n}: that product no longer exists.")
            price = (
                product.price
                if raw.get("unit_price") in (None, "")
                else whole_kes(raw["unit_price"], f"Line {n} unit price")
            )
            desc = clean_text(raw.get("description") or product.name, f"Line {n} description", min_len=2, max_len=200)
            # Credit notes copy the invoice line's VAT status, even if the product changed since.
            exempt = flag(raw["vat_exempt"]) if allow_restock and "vat_exempt" in raw else product.vat_exempt
            items.append(
                Item(desc, qty, price, exempt, product, restock=allow_restock and flag(raw.get("restock")))
            )
        else:
            desc = clean_text(raw.get("description"), f"Line {n} description", min_len=2, max_len=200)
            price = whole_kes(raw.get("unit_price"), f"Line {n} unit price")
            items.append(Item(desc, qty, price, flag(raw.get("vat_exempt"))))
    return items


def parse_payment(data, *, required=True) -> dict | None:
    if not data:
        if required:
            raise ValueError("Enter the payment.")
        return None
    method = data.get("method")
    if method not in {"mpesa", "cash", "bank"}:
        raise ValueError("Choose how they paid: M-Pesa, Cash or Bank.")
    reference = clean_text(data.get("reference"), "Reference", max_len=60)
    if method == "mpesa" and not reference:
        raise ValueError("Enter the M-Pesa code, for example TKB7XY12AB.")
    overpay = data.get("overpay") or "refund"
    return {
        "amount": whole_kes(data.get("amount"), "Amount paid", minimum=1),
        "method": method,
        "reference": reference.upper() if method == "mpesa" else reference,
        "overpay": overpay,
    }


def customer_from(data, request) -> Customer:
    if flag(data.get("walk_in")):
        return services.walk_in_customer()
    if data.get("customer_id"):
        return get_object_or_404(Customer, pk=data["customer_id"], active=True)
    if isinstance(data.get("new_customer"), dict):
        fields = parse_customer_fields(data["new_customer"], owner=is_owner(request.user))
        c = Customer.objects.create(**fields)
        services.audit(request.user, "create", "customer", c.pk, f"Added customer {c.name}")
        return c
    raise ValueError("Pick a customer, add a new one, or choose Walk-in.")


# ---------- auth ----------


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return Response({"ok": True})


@public_view(["POST"])
def login_view(request):
    data = body(request)
    email = auth.normalize_email(data.get("email"))
    password = str(data.get("password") or "")
    if not email or not password:
        return Response({"detail": "Enter your email and password."}, status=400)
    locked = auth.check_lock(email)
    if locked:
        return Response({"detail": locked}, status=429)
    user = auth.find_user(email)
    ok = user and authenticate(request, username=user.get_username(), password=password)
    if not ok:
        return Response({"detail": auth.record_failure(email)}, status=400)
    auth.clear_failures(email)
    auth.start_session(request._request, user)
    services.audit(user, "login", "user", user.pk, f"{user.email} logged in")
    return Response(user_json(user))


@ledger_view(["POST"])
def logout_view(request):
    logout(request._request)
    return Response({"ok": True})


@ledger_view(["POST"])
def logout_all(request):
    auth.end_all_sessions(request.user)
    services.audit(request.user, "logout_all", "user", request.user.pk, "Logged out on every device")
    logout(request._request)
    return Response({"ok": True})


@ledger_view(["GET"])
def me(request):
    s = BusinessSettings.load()
    return Response(
        {
            **user_json(request.user),
            "can_void": is_owner(request.user) or s.staff_can_void,
            "can_set_vat_exempt": is_owner(request.user) or s.staff_can_set_vat_exempt,
            "vat_percent": s.vat_percent,
        }
    )


@public_view(["POST"])
def reset_request(request):
    email = auth.normalize_email(body(request).get("email"))
    key = f"ledger-reset:{email}"
    if cache.get(key, 0) < 10:
        cache.set(key, cache.get(key, 0) + 1, 3600)
        user = auth.find_user(email) if email else None
        if user:
            code = auth.issue_reset_code(user)
            if code:
                emails.send_reset_code(user, code)
    return Response({"detail": "If that email has an account, we sent a 6-digit code to it. Check your inbox."})


@public_view(["POST"])
def reset_confirm(request):
    data = body(request)
    email = auth.normalize_email(data.get("email"))
    user = auth.find_user(email)
    if not user:
        return Response({"detail": "This code has expired or was already used. Ask for a new code."}, status=400)
    error = auth.check_reset_code(user, data.get("code", ""))
    if error:
        return Response({"detail": error}, status=400)
    password = str(data.get("password") or "")
    try:
        validate_password(password, user)
    except ValidationError as e:
        return Response({"detail": " ".join(e.messages)}, status=400)
    user.set_password(password)
    user.save(update_fields=["password"])
    auth.end_all_sessions(user)
    auth.clear_failures(email)
    services.audit(user, "password_reset", "user", user.pk, f"{user.email} reset their password")
    return Response({"detail": "Password changed. Log in with your new password."})


@ledger_view(["POST"])
def change_password(request):
    data = body(request)
    if not request.user.check_password(str(data.get("current") or "")):
        return Response({"detail": "Your current password is wrong."}, status=400)
    new = str(data.get("new") or "")
    try:
        validate_password(new, request.user)
    except ValidationError as e:
        return Response({"detail": " ".join(e.messages)}, status=400)
    request.user.set_password(new)
    request.user.save(update_fields=["password"])
    auth.end_all_sessions(request.user)
    auth.start_session(request._request, request.user)
    services.audit(request.user, "password_change", "user", request.user.pk, "Changed password")
    return Response({"ok": True})


# ---------- users (owner) ----------


@ledger_view(["GET", "POST"], owner_only=True)
def users(request):
    if request.method == "GET":
        qs = (
            User.objects.filter(ledger_profile__isnull=False)
            .select_related("ledger_profile")
            .order_by("-is_active", "email")
        )
        return Response([user_json(u) for u in qs])
    data = body(request)
    name = clean_text(data.get("name"), "Name", min_len=2, max_len=150)
    email = auth.normalize_email(data.get("email"))
    try:
        validate_email(email)
    except ValidationError:
        raise ValueError("Email must look like name@example.com.") from None
    if User.objects.filter(email__iexact=email).exists():
        raise ValueError("Someone already uses this email.")
    password = str(data.get("password") or "")
    first, _, last = name.partition(" ")
    user = User(username=email, email=email, first_name=first[:150], last_name=last[:150])
    try:
        validate_password(password, user)
    except ValidationError as e:
        raise ValueError("Starting password: " + " ".join(e.messages)) from None
    with transaction.atomic():
        user.set_password(password)
        user.save()
        Profile.objects.create(user=user, role=Role.STAFF)
        services.audit(request.user, "create", "user", user.pk, f"Added staff member {email}")
    return Response(user_json(user), status=201)


@ledger_view(["POST"], owner_only=True)
def remove_user(request, pk):
    user = get_object_or_404(User, pk=pk, ledger_profile__isnull=False)
    if user.ledger_profile.is_owner:
        raise ValueError("The owner account cannot be removed.")
    user.is_active = False
    user.save(update_fields=["is_active"])
    auth.end_all_sessions(user)
    services.audit(request.user, "remove", "user", user.pk, f"Removed staff member {user.email}")
    return Response(user_json(user))


@ledger_view(["POST"], owner_only=True)
def restore_user(request, pk):
    user = get_object_or_404(User, pk=pk, ledger_profile__isnull=False)
    user.is_active = True
    user.save(update_fields=["is_active"])
    services.audit(request.user, "restore", "user", user.pk, f"Restored staff member {user.email}")
    return Response(user_json(user))


# ---------- settings ----------

SETTINGS_TEXT = {
    "kra_pin": ("KRA PIN", 20),
    "mpesa_paybill": ("M-Pesa paybill", 10),
    "mpesa_account": ("Paybill account", 40),
    "mpesa_till": ("M-Pesa till", 10),
    "bank_name": ("Bank name", 80),
    "bank_branch": ("Bank branch", 80),
    "bank_account_name": ("Account name", 120),
    "bank_account_number": ("Account number", 40),
}


def settings_json(s):
    return {
        **{k: getattr(s, k) for k in SETTINGS_TEXT},
        "vat_percent": s.vat_percent,
        "payment_terms_days": s.payment_terms_days,
        "quotation_valid_days": s.quotation_valid_days,
        "staff_can_void": s.staff_can_void,
        "staff_can_set_vat_exempt": s.staff_can_set_vat_exempt,
    }


@ledger_view(["GET", "PUT"], owner_only=True)
def settings_view(request):
    s = BusinessSettings.load()
    if request.method == "PUT":
        data = body(request)
        for key, (label, n) in SETTINGS_TEXT.items():
            if key in data:
                setattr(s, key, clean_text(data[key], label, max_len=n))
        if s.mpesa_paybill and not s.mpesa_paybill.isdigit():
            raise ValueError("M-Pesa paybill must be digits only, for example 247247.")
        if s.mpesa_till and not s.mpesa_till.isdigit():
            raise ValueError("M-Pesa till must be digits only, for example 5123456.")
        if "vat_percent" in data:
            s.vat_percent = whole_qty(data["vat_percent"], "VAT %", minimum=0, maximum=50)
        if "payment_terms_days" in data:
            s.payment_terms_days = whole_qty(data["payment_terms_days"], "Payment terms (days)", minimum=0, maximum=365)
        if "quotation_valid_days" in data:
            s.quotation_valid_days = whole_qty(
                data["quotation_valid_days"], "Quotation valid (days)", minimum=1, maximum=365
            )
        for key in ("staff_can_void", "staff_can_set_vat_exempt"):
            if key in data:
                setattr(s, key, flag(data[key]))
        s.save()
        services.audit(request.user, "update", "settings", 1, "Changed business settings")
    return Response(settings_json(s))


# ---------- customers ----------


@ledger_view(["GET", "POST"])
def customers(request):
    if request.method == "POST":
        fields = parse_customer_fields(body(request), owner=is_owner(request.user))
        c = Customer.objects.create(**fields)
        services.audit(request.user, "create", "customer", c.pk, f"Added customer {c.name}")
        return Response(customer_json(c), status=201)
    qs = Customer.objects.filter(is_walk_in=False)
    q = request.query_params.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q.lstrip("0")) | Q(email__icontains=q))
    rows = list(qs.filter(active=request.query_params.get("active", "1") != "0")[:200])
    balances = services.balances_for([c.pk for c in rows])
    return Response([customer_json(c, balance=balances[c.pk]) for c in rows])


@ledger_view(["GET", "PATCH"])
def customer_detail(request, pk):
    c = get_object_or_404(Customer, pk=pk)
    if request.method == "PATCH":
        fields = parse_customer_fields(body(request), partial=True, owner=is_owner(request.user))
        for k, v in fields.items():
            setattr(c, k, v)
        c.save()
        services.audit(request.user, "update", "customer", c.pk, f"Changed customer {c.name}: {', '.join(fields)}")
    tab = c.tabs.filter(closed_at__isnull=True).first()
    lines = services.unbilled_lines(c)
    docs = services.invoices_with_balance().filter(customer=c).select_related("customer")[:100]
    others = (
        services.documents_with_balance()
        .filter(customer=c)
        .exclude(doc_type=DocType.INVOICE)
        .select_related("customer")[:100]
    )
    pays = (
        Payment.objects.filter(customer=c)
        .select_related("customer")
        .prefetch_related("allocations__invoice", "receipts")[:100]
    )
    return Response(
        {
            **customer_json(c),
            "tab_open": bool(tab),
            "tab_lines": [
                {
                    "id": sl.pk,
                    "description": sl.description,
                    "qty": sl.qty,
                    "unit_price": sl.unit_price,
                    "vat_exempt": sl.vat_exempt,
                    "created_at": sl.created_at,
                }
                for sl in lines
            ],
            "invoices": [document_json(d) for d in docs],
            "documents": [document_json(d) for d in others],
            "payments": [payment_json(p) for p in pays],
        }
    )


@ledger_view(["POST"])
def tab_bill(request, pk):
    c = get_object_or_404(Customer, pk=pk)
    invoice = services.bill_tab(request.user, c, close=False)
    return Response(document_json(invoice, detail=True), status=201)


@ledger_view(["POST"])
def tab_close(request, pk):
    c = get_object_or_404(Customer, pk=pk)
    invoice = services.bill_tab(request.user, c, close=True)
    return Response({"invoice": document_json(invoice, detail=True) if invoice else None})


@ledger_view(["POST"])
def tab_line_remove(request, pk):
    line = get_object_or_404(SaleLine, pk=pk)
    services._can_void(request.user)
    reason = clean_text(body(request).get("reason"), "Reason", min_len=3, max_len=200)
    services.remove_tab_line(request.user, line, reason)
    return Response({"ok": True})


@ledger_view(["POST"])
def statement(request, pk):
    c = get_object_or_404(Customer, pk=pk)
    data = body(request)
    end = parse_date(data.get("to"), "To date") or services.today()
    start = parse_date(data.get("from"), "From date") or end.replace(day=1)
    if start > end:
        raise ValueError("The From date must be on or before the To date.")
    content = pdf.statement_pdf(c, start, end, unbilled=services.unbilled_total(c))
    services.audit(request.user, "statement", "customer", c.pk, f"Statement for {c.name} {start} to {end}")
    if flag(data.get("email")):
        if not c.email:
            raise ValueError(f"{c.name} has no email address. Add one first.")
        if not emails.send_statement(c, content, f"{pdf.day(start)} to {pdf.day(end)}"):
            raise ValueError("The email could not be sent. Check the email settings, then try again.")
        return Response({"detail": f"Statement emailed to {c.email}."})
    return pdf_response(content, f"statement-{c.pk}-{start}-{end}.pdf")


@ledger_view(["POST"], owner_only=True)
def refund(request, pk):
    c = get_object_or_404(Customer, pk=pk)
    data = body(request)
    amount = whole_kes(data.get("amount"), "Refund amount", minimum=1)
    note = clean_text(data.get("note"), "How it was refunded", min_len=3, max_len=200)
    services.refund_credit(request.user, c, amount, note)
    return Response(customer_json(c))


# ---------- products and stock ----------


def _owner_only_product_fields(data, request):
    if "cost_price" in data and not is_owner(request.user):
        raise ValueError("Only the owner can see or set cost prices.")
    if "vat_exempt" in data and not (is_owner(request.user) or BusinessSettings.load().staff_can_set_vat_exempt):
        raise ValueError("Only the owner can set VAT exempt. The owner can allow staff in Settings.")


def parse_product_fields(data, *, partial=False) -> dict:
    out = {}
    if not partial or "name" in data:
        out["name"] = clean_text(data.get("name"), "Product name", min_len=2, max_len=160)
    if not partial or "price" in data:
        out["price"] = whole_kes(data.get("price"), "Selling price (excluding VAT)")
    if "unit" in data:
        out["unit"] = clean_text(data.get("unit"), "Unit", min_len=1, max_len=30) or "piece"
    if "cost_price" in data:
        out["cost_price"] = None if data["cost_price"] in (None, "") else whole_kes(data["cost_price"], "Cost price")
    if "vat_exempt" in data:
        out["vat_exempt"] = flag(data["vat_exempt"])
    if "reorder_level" in data:
        out["reorder_level"] = whole_qty(data["reorder_level"], "Reorder level", minimum=0)
    if "active" in data:
        out["active"] = flag(data["active"])
    return out


def _name_taken(name, exclude=None) -> bool:
    qs = Product.objects.filter(name__iexact=name)
    if exclude:
        qs = qs.exclude(pk=exclude)
    return qs.exists()


@ledger_view(["GET", "POST"])
def products(request):
    owner = is_owner(request.user)
    if request.method == "POST":
        data = body(request)
        _owner_only_product_fields(data, request)
        fields = parse_product_fields(data)
        if _name_taken(fields["name"]):
            raise ValueError("A product with this name already exists.")
        opening = whole_qty(data.get("opening_qty", 0), "Starting stock", minimum=0)
        p = services.add_product(request.user, opening_qty=opening, **fields)
        return Response(product_json(p, opening, owner), status=201)
    qs = Product.objects.all()
    q = request.query_params.get("q", "").strip()
    if q:
        qs = qs.filter(name__icontains=q)
    qs = qs.filter(active=request.query_params.get("active", "1") != "0")
    rows = list(qs[:500])
    levels = services.stock_levels([p.pk for p in rows])
    return Response([product_json(p, levels[p.pk], owner) for p in rows])


@ledger_view(["GET", "PATCH"])
def product_detail(request, pk):
    p = get_object_or_404(Product, pk=pk)
    owner = is_owner(request.user)
    if request.method == "PATCH":
        data = body(request)
        _owner_only_product_fields(data, request)
        if "opening_qty" in data or "on_hand" in data:
            raise ValueError("Stock is never edited directly. Use Receive or Take out.")
        fields = parse_product_fields(data, partial=True)
        if "name" in fields and _name_taken(fields["name"], exclude=p.pk):
            raise ValueError("A product with this name already exists.")
        for k, v in fields.items():
            setattr(p, k, v)
        p.save()
        services.audit(request.user, "update", "product", p.pk, f"Changed product {p.name}: {', '.join(fields)}")
    moves = p.movements.select_related("created_by")[:100]
    return Response(
        {
            **product_json(p, p.on_hand(), owner),
            "movements": [
                {
                    "id": m.pk,
                    "kind": m.kind,
                    "kind_label": m.get_kind_display(),
                    "qty": m.qty,
                    "note": m.note,
                    "at": m.created_at,
                    "by": m.created_by.get_full_name() or m.created_by.email if m.created_by else "",
                    **({"unit_cost": m.unit_cost} if owner else {}),
                }
                for m in moves
            ],
        }
    )


@ledger_view(["POST"])
def product_receive(request, pk):
    p = get_object_or_404(Product, pk=pk)
    data = body(request)
    qty = whole_qty(data.get("qty"), "Quantity received")
    unit_cost = None
    if data.get("unit_cost") not in (None, ""):
        if not is_owner(request.user):
            raise ValueError("Only the owner can enter cost prices.")
        unit_cost = whole_kes(data["unit_cost"], "Cost per item")
    note = clean_text(data.get("note"), "Note", max_len=200)
    services.receive_stock(request.user, p, qty, unit_cost, note)
    return Response(product_json(p, p.on_hand(), is_owner(request.user)))


@ledger_view(["POST"])
def product_take_out(request, pk):
    p = get_object_or_404(Product, pk=pk)
    data = body(request)
    qty = whole_qty(data.get("qty"), "Quantity to take out")
    reason = clean_text(data.get("reason"), "Reason", min_len=3, max_len=200)
    services.take_out_stock(request.user, p, qty, reason)
    return Response(product_json(p, p.on_hand(), is_owner(request.user)))


@ledger_view(["GET"])
def buy_list(request):
    since = services.today() - timedelta(days=90)
    sold = dict(
        StockMovement.objects.filter(kind=StockMovement.Kind.SALE, created_at__date__gte=since)
        .values_list("product_id")
        .annotate(t=Sum("qty"))
        .values_list("product_id", "t")
    )
    voided = dict(
        StockMovement.objects.filter(kind=StockMovement.Kind.VOID, created_at__date__gte=since)
        .values_list("product_id")
        .annotate(t=Sum("qty"))
        .values_list("product_id", "t")
    )
    prods = list(Product.objects.filter(active=True))
    levels = services.stock_levels([p.pk for p in prods])
    rows = []
    from .money import buy_suggestion

    for p in prods:
        sold_qty = max(-(sold.get(p.pk) or 0) - (voided.get(p.pk) or 0), 0)
        item = buy_suggestion(p.reorder_level, levels[p.pk], sold_qty)
        if item:
            rows.append(
                {
                    "id": p.pk,
                    "name": p.name,
                    "unit": p.unit,
                    "on_hand": levels[p.pk],
                    "reorder_level": p.reorder_level,
                    "sold_last_3_months": sold_qty,
                    "target": item.target,
                    "order_qty": item.order_qty,
                    "basis": "Reorder level + average monthly sales (last 3 months)"
                    if item.used_history
                    else "No sales in the last 3 months: target is the reorder level only",
                }
            )
    rows.sort(key=lambda r: (r["on_hand"] > 0, r["name"].lower()))
    return Response(rows)


# ---------- sales, quotations, documents ----------


@ledger_view(["POST"])
def sales(request):
    data = body(request)
    items = parse_items(data.get("items"))
    paid_now = parse_payment(data.get("paid_now"), required=False)
    due_on = parse_date(data.get("due_on"), "Due date")
    if due_on and due_on < services.today():
        raise ValueError("The due date cannot be in the past.")
    with transaction.atomic():
        customer = customer_from(data, request)
        result = services.record_sale(request.user, customer, items, payment=paid_now, due_on=due_on)
        receipt = None
        if result.payment and flag(data.get("receipt")):
            receipt = services.make_receipt(request.user, result.payment)
    return Response(
        {
            "customer": customer_json(customer),
            "invoice": document_json(result.invoice, detail=True) if result.invoice else None,
            "receipt": document_json(receipt, detail=True) if receipt else None,
            "on_tab": bool(result.tab),
            "overpaid": result.overpaid,
            "alert": result.alert.message if result.alert else None,
        },
        status=201,
    )


@ledger_view(["POST"])
def quotations(request):
    data = body(request)
    items = parse_items(data.get("items"))
    valid_until = parse_date(data.get("valid_until"), "Valid until")
    lead = None
    if data.get("lead_id"):
        lead = get_object_or_404(QuoteRequest, pk=data["lead_id"])
    with transaction.atomic():
        customer = customer_from(data, request)
        if customer.is_walk_in:
            raise ValueError("A quotation needs the customer's name. Pick or add the customer.")
        qtn = services.create_quotation(request.user, customer, items, valid_until=valid_until, lead=lead)
    return Response(document_json(qtn, detail=True), status=201)


@ledger_view(["GET"])
def documents(request):
    qp = request.query_params
    qs = services.documents_with_balance()
    if qp.get("type") in DocType.values:
        qs = qs.filter(doc_type=qp["type"])
    if qp.get("customer"):
        qs = qs.filter(customer_id=qp["customer"])
    if qp.get("q"):
        qs = qs.filter(Q(number__icontains=qp["q"]) | Q(customer__name__icontains=qp["q"]))
    start = parse_date(qp.get("from"), "From date")
    end = parse_date(qp.get("to"), "To date")
    if start:
        qs = qs.filter(issued_on__gte=start)
    if end:
        qs = qs.filter(issued_on__lte=end)
    status = qp.get("status")
    if status == "void":
        qs = qs.filter(void=True)
    elif status:
        qs = qs.filter(void=False)
        if status in {"paid", "unpaid", "overdue"}:
            qs = qs.filter(doc_type=DocType.INVOICE)
        if status == "paid":
            qs = qs.filter(bal__lte=0)
        elif status == "unpaid":
            qs = qs.filter(bal__gt=0)
        elif status == "overdue":
            qs = qs.filter(bal__gt=0, due_on__lt=services.today())
    qs = qs.select_related("customer").order_by("-issued_on", "-id")[:300]
    return Response([document_json(d) for d in qs])


def _doc(pk):
    return get_object_or_404(Document.objects.select_related("customer", "related", "payment"), pk=pk)


@ledger_view(["GET"])
def document_detail(request, pk):
    return Response(document_json(_doc(pk), detail=True))


@ledger_view(["GET"])
def document_pdf(request, pk):
    d = _doc(pk)
    try:
        content = pdf.document_pdf(d)
    except OSError:  # WeasyPrint's system libraries missing on the server
        logger.exception("PDF rendering failed")
        return Response({"detail": "The PDF maker is not working on the server. Tell the developer."}, status=503)
    return pdf_response(content, f"{d.number}.pdf", inline=request.query_params.get("download") != "1")


@ledger_view(["POST"])
def document_void(request, pk):
    reason = clean_text(body(request).get("reason"), "Reason", min_len=3, max_len=200)
    services.void_document(request.user, _doc(pk), reason)
    return Response(document_json(_doc(pk), detail=True))


@ledger_view(["POST"])
def document_email(request, pk):
    d = _doc(pk)
    to = str(body(request).get("to") or d.customer.email).strip()
    try:
        validate_email(to)
    except ValidationError:
        raise ValueError(f"{d.customer.name} has no valid email. Type one, like name@example.com.") from None
    if not emails.send_document(d, to):
        raise ValueError("The email could not be sent. Check the email settings, then try again.")
    services.audit(request.user, "email", "document", d.pk, f"Emailed {d.number} to {to}")
    return Response({"detail": f"{d.number} emailed to {to}."})


@ledger_view(["POST"])
def document_credit_note(request, pk):
    d = _doc(pk)
    if d.doc_type != DocType.INVOICE:
        raise ValueError("Credit notes are issued against invoices.")
    data = body(request)
    items = parse_items(data.get("items"), allow_restock=True)
    reason = clean_text(data.get("reason"), "Reason", min_len=3, max_len=200)
    overpay = data.get("overpay") or "refund"
    cn = services.credit_note(request.user, d, items, reason, overpay=overpay)
    return Response(document_json(cn, detail=True), status=201)


@ledger_view(["POST"])
def document_convert(request, pk):
    d = _doc(pk)
    result = services.convert_quotation(request.user, d)
    return Response(document_json(result.invoice, detail=True), status=201)


@ledger_view(["PATCH"])
def document_update(request, pk):
    """Only fields that do not change money: eTIMS number, and part-payment permission (owner)."""
    d = _doc(pk)
    data = body(request)
    changed = []
    if "etims_number" in data:
        d.etims_number = clean_text(data["etims_number"], "eTIMS number", max_len=40)
        changed.append("eTIMS number")
    if "allow_partial" in data:
        if not is_owner(request.user):
            raise ValueError("Only the owner can allow part payments.")
        d.allow_partial = None if data["allow_partial"] is None else flag(data["allow_partial"])
        changed.append("part payments")
    if set(data) - {"etims_number", "allow_partial"}:
        raise ValueError("Issued documents cannot be edited. Void it or issue a credit note.")
    d.save(update_fields=["etims_number", "allow_partial"])
    services.audit(request.user, "update", "document", d.pk, f"Changed {d.number}: {', '.join(changed)}")
    return Response(document_json(d, detail=True))


# ---------- payments ----------


@ledger_view(["GET", "POST"])
def payments(request):
    if request.method == "POST":
        data = body(request)
        customer = get_object_or_404(Customer, pk=data.get("customer_id"))
        p = parse_payment(data)
        received_on = parse_date(data.get("received_on"), "Date received") or services.today()
        if received_on > services.today():
            raise ValueError("The date received cannot be in the future.")
        invoice_ids = data.get("invoice_ids") or None
        if invoice_ids is not None and (
            not isinstance(invoice_ids, list) or not all(isinstance(i, int) for i in invoice_ids)
        ):
            raise ValueError("Pick the invoices from the list.")
        with transaction.atomic():
            payment, extra = services.record_payment(
                request.user,
                customer,
                amount=p["amount"],
                method=p["method"],
                reference=p["reference"],
                received_on=received_on,
                invoice_ids=invoice_ids,
                overpay=p["overpay"],
            )
            receipt = services.make_receipt(request.user, payment) if flag(data.get("receipt")) else None
        payment.refresh_from_db()
        return Response(
            {**payment_json(payment), "overpaid": extra, "receipt": document_json(receipt) if receipt else None},
            status=201,
        )
    qs = Payment.objects.select_related("customer").prefetch_related("allocations__invoice", "receipts")
    qp = request.query_params
    if qp.get("customer"):
        qs = qs.filter(customer_id=qp["customer"])
    start = parse_date(qp.get("from"), "From date")
    end = parse_date(qp.get("to"), "To date")
    if start:
        qs = qs.filter(received_on__gte=start)
    if end:
        qs = qs.filter(received_on__lte=end)
    return Response([payment_json(p) for p in qs[:300]])


@ledger_view(["POST"])
def payment_receipt(request, pk):
    p = get_object_or_404(Payment, pk=pk)
    receipt = services.make_receipt(request.user, p)
    return Response(document_json(receipt, detail=True), status=201)


@ledger_view(["POST"])
def payment_void(request, pk):
    services._can_void(request.user)
    p = get_object_or_404(Payment, pk=pk)
    reason = clean_text(body(request).get("reason"), "Reason", min_len=3, max_len=200)
    services.void_payment(request.user, p, reason)
    p.refresh_from_db()
    return Response(payment_json(p))


# ---------- reports ----------


@ledger_view(["GET"])
def home(request):
    t = services.today()
    received = Payment.objects.filter(void=False, received_on=t).exclude(method=Payment.Method.CREDIT_NOTE)
    from .models import Refund

    refunds_today = Refund.objects.filter(on=t, payment__void=False).aggregate(s=Coalesce(Sum("amount"), 0))["s"]
    open_inv = services.invoices_with_balance().filter(void=False, bal__gt=0)
    prods = list(Product.objects.filter(active=True))
    levels = services.stock_levels([p.pk for p in prods])
    recent = services.documents_with_balance().select_related("customer").order_by("-created_at")[:8]
    return Response(
        {
            "cash_collected": received.aggregate(s=Coalesce(Sum("amount"), 0))["s"] - refunds_today,
            "refunds_today": refunds_today,
        "collected_by_method": {
                row["method"]: row["s"] for row in received.values("method").annotate(s=Sum("amount"))
            },
            "invoiced": Document.objects.filter(doc_type=DocType.INVOICE, void=False, issued_on=t).aggregate(
                s=Coalesce(Sum("total"), 0)
            )["s"],
            "owed": open_inv.aggregate(s=Coalesce(Sum("bal"), 0))["s"],
            "overdue_count": open_inv.filter(due_on__lt=t).count(),
            "reorder_count": sum(1 for p in prods if levels[p.pk] <= p.reorder_level),
            "alerts": [
                {"id": a.pk, "message": a.message, "at": a.created_at}
                for a in Alert.objects.filter(resolved=False)[:10]
            ],
            "new_leads": QuoteRequest.objects.filter(status="new").count(),
            "recent": [document_json(d) for d in recent],
        }
    )


@ledger_view(["GET"])
def report_money(request):
    start, end = period(request)
    pays = Payment.objects.filter(void=False, received_on__range=(start, end)).exclude(
        method=Payment.Method.CREDIT_NOTE
    )
    from .models import Refund

    refunds = Refund.objects.filter(payment__void=False, on__range=(start, end))
    by_day = {}
    for row in pays.values("received_on").annotate(s=Sum("amount")).order_by("received_on"):
        by_day[str(row["received_on"])] = {"in": row["s"], "out": 0}
    for row in refunds.values("on").annotate(s=Sum("amount")):
        by_day.setdefault(str(row["on"]), {"in": 0, "out": 0})["out"] += row["s"]
    data = {
        "from": start,
        "to": end,
        "money_in": pays.aggregate(s=Coalesce(Sum("amount"), 0))["s"],
        "by_method": {r["method"]: r["s"] for r in pays.values("method").annotate(s=Sum("amount"))},
        "refunds_out": refunds.aggregate(s=Coalesce(Sum("amount"), 0))["s"],
        "by_day": [{"day": k, **v} for k, v in sorted(by_day.items())],
    }
    if is_owner(request.user):
        received = StockMovement.objects.filter(
            kind=StockMovement.Kind.RECEIVE, created_at__date__range=(start, end), unit_cost__isnull=False
        )
        data["stock_bought"] = sum(m.qty * m.unit_cost for m in received)
    return Response(data)


@ledger_view(["GET"])
def report_aging(request):
    t = services.today()
    buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    per_customer = {}
    for inv in services.invoices_with_balance().filter(void=False, bal__gt=0).select_related("customer"):
        age = (t - inv.issued_on).days
        key = "0-30" if age <= 30 else "31-60" if age <= 60 else "61-90" if age <= 90 else "90+"
        buckets[key] += inv.bal
        row = per_customer.setdefault(
            inv.customer_id,
            {"customer": inv.customer.name, "id": inv.customer_id, **{k: 0 for k in buckets}, "total": 0},
        )
        row[key] += inv.bal
        row["total"] += inv.bal
    return Response(
        {
            "buckets": buckets,
            "total": sum(buckets.values()),
            "customers": sorted(per_customer.values(), key=lambda r: -r["total"]),
        }
    )


def _billed_lines(start, end):
    return SaleLine.objects.filter(invoice__void=False, invoice__issued_on__range=(start, end), voided=False)


@ledger_view(["GET"])
def report_sales(request):
    start, end = period(request)
    invs = Document.objects.filter(doc_type=DocType.INVOICE, void=False, issued_on__range=(start, end))
    by_customer = list(
        invs.values("customer_id", "customer__name")
        .annotate(total=Sum("total"), count=Count("id"))
        .order_by("-total")[:100]
    )
    by_product = {}
    for sl in _billed_lines(start, end).select_related("product"):
        key = sl.product.name if sl.product_id else "Custom jobs and services"
        row = by_product.setdefault(key, {"name": key, "qty": 0, "sales": 0})
        row["qty"] += sl.qty
        row["sales"] += sl.qty * sl.unit_price
    return Response(
        {
            "from": start,
            "to": end,
            "total": invs.aggregate(s=Coalesce(Sum("total"), 0))["s"],
            "by_customer": [
                {"id": r["customer_id"], "name": r["customer__name"], "total": r["total"], "count": r["count"]}
                for r in by_customer
            ],
            "by_product": sorted(by_product.values(), key=lambda r: -r["sales"]),
        }
    )


@ledger_view(["GET"], owner_only=True)
def report_profit(request):
    start, end = period(request)
    rows, revenue, cost, unknown = {}, 0, 0, 0
    for sl in _billed_lines(start, end).select_related("product"):
        sale = sl.qty * sl.unit_price
        key = sl.product.name if sl.product_id else "Custom jobs and services"
        row = rows.setdefault(key, {"name": key, "sales": 0, "cost": 0, "profit": 0, "cost_unknown": 0})
        row["sales"] += sale
        revenue += sale
        if sl.unit_cost is None:
            row["cost_unknown"] += sale
            unknown += sale
        else:
            c = sl.qty * sl.unit_cost
            row["cost"] += c
            row["profit"] += sale - c
            cost += c
    return Response(
        {
            "from": start,
            "to": end,
            "sales_ex_vat": revenue,
            "cost": cost,
            "profit": revenue - unknown - cost,
            "sales_without_cost": unknown,
            "note": "Profit counts only items with a cost price. Sales without a cost price are listed separately.",
            "items": sorted(rows.values(), key=lambda r: -r["profit"]),
        }
    )


@ledger_view(["GET"])
def report_vat(request):
    year = int(request.query_params.get("year") or services.today().year)
    months = {m: {"month": m, "taxable": 0, "exempt": 0, "vat": 0} for m in range(1, 13)}
    docs = Document.objects.filter(doc_type__in=[DocType.INVOICE, DocType.CREDIT_NOTE], void=False, year=year)
    for d in docs.prefetch_related("lines"):
        sign = 1 if d.doc_type == DocType.INVOICE else -1
        row = months[d.issued_on.month]
        for ln in d.lines.all():
            row["exempt" if ln.vat_exempt else "taxable"] += sign * ln.amount
            row["vat"] += sign * ln.vat
    return Response(
        {
            "year": year,
            "months": list(months.values()),
            "note": "Credit notes are subtracted in the month they were issued.",
        }
    )


# ---------- alerts, leads, uploads, QR, audit ----------


@ledger_view(["GET"])
def alerts(request):
    return Response(
        [
            {"id": a.pk, "message": a.message, "resolved": a.resolved, "at": a.created_at, "customer_id": a.customer_id}
            for a in Alert.objects.all()[:100]
        ]
    )


@ledger_view(["POST"])
def alert_resolve(request, pk):
    Alert.objects.filter(pk=pk).update(resolved=True)
    return Response({"ok": True})


def lead_json(q):
    return {
        "id": q.pk,
        "name": q.name,
        "company": q.company,
        "phone": q.phone,
        "email": q.email,
        "needs": q.needs,
        "quantity": q.quantity,
        "required_date": q.required_date,
        "status": q.status,
        "created_at": q.created_at,
    }


@ledger_view(["GET"])
def leads(request):
    qs = QuoteRequest.objects.all()
    if request.query_params.get("status"):
        qs = qs.filter(status=request.query_params["status"])
    return Response([lead_json(q) for q in qs[:300]])


@ledger_view(["PATCH"])
def lead_detail(request, pk):
    q = get_object_or_404(QuoteRequest, pk=pk)
    status = body(request).get("status")
    if status not in dict(QuoteRequest.STATUS_CHOICES):
        raise ValueError("Status must be New, Contacted, Quoted or Closed.")
    q.status = status
    q.save(update_fields=["status", "updated_at"])
    services.audit(request.user, "update", "lead", q.pk, f"Lead from {q.name} marked {status}")
    return Response(lead_json(q))


@ledger_view(["GET"])
def uploads(request):
    from pathlib import Path

    return Response(
        [
            {
                "id": f.pk,
                "reference": f"ES-F{f.pk}",
                "original_filename": f.original_filename,
                "converted_filename": Path(f.converted_file.name).name if f.converted_file else "",
                "name": f.name,
                "phone": f.phone,
                "note": f.note,
                "created_at": f.created_at,
            }
            for f in FileSubmission.objects.all()[:300]
        ]
    )


@ledger_view(["GET"])
def upload_file(request, pk, kind):
    from quotes.views import _file_response

    f = get_object_or_404(FileSubmission, pk=pk)
    field = f.uploaded_file if kind == "original" else f.converted_file if kind == "converted" else None
    if not field:
        return Response({"detail": "That file is not available."}, status=404)
    try:
        return _file_response(field)
    except (FileNotFoundError, OSError):
        return Response({"detail": "This file is no longer stored on the server."}, status=404)


def upload_page_url() -> str:
    return f"{settings.ESICOM_PUBLIC_SITE_URL.rstrip('/')}/upload/"


@ledger_view(["GET"])
def qr_code(request):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=4)
    qr.add_data(upload_page_url())
    qr.make(fit=True)
    out = BytesIO()
    qr.make_image(fill_color="#10243d", back_color="white").save(out, format="PNG")
    resp = HttpResponse(out.getvalue(), content_type="image/png")
    resp["Cache-Control"] = "private, max-age=300"
    resp["X-Upload-Url"] = upload_page_url()
    return resp


@ledger_view(["GET"])
def qr_info(request):
    return Response({"url": upload_page_url()})


@ledger_view(["GET"], owner_only=True)
def audit_log(request):
    qs = AuditLog.objects.select_related("user")
    if request.query_params.get("q"):
        qs = qs.filter(summary__icontains=request.query_params["q"])
    return Response(
        [
            {
                "id": a.pk,
                "at": a.at,
                "user": (a.user.get_full_name() or a.user.email) if a.user else "System",
                "action": a.action,
                "entity": a.entity,
                "entity_id": a.entity_id,
                "summary": a.summary,
            }
            for a in qs[:500]
        ]
    )
