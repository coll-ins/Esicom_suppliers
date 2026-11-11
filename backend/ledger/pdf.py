"""Render invoices, receipts, quotations, credit notes and statements to A4 PDF (WeasyPrint)."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from django.template.loader import render_to_string

from .money import VAT_PERCENT, line_amount, line_vat

ASSETS = Path(__file__).resolve().parent

TITLES = {"INV": "Invoice", "RCP": "Receipt", "QTN": "Quotation", "CN": "Credit note"}
TOTAL_LABELS = {
    "INV": "Total due (KES)",
    "RCP": "Amount paid (KES)",
    "QTN": "Total (KES)",
    "CN": "Total credited (KES)",
}


@dataclass
class DocLine:
    description: str
    qty: int
    unit_price: int
    vat_exempt: bool = False


@dataclass
class BillTo:
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    kra_pin: str = ""


@dataclass
class Business:
    """Owner-entered settings. A blank field is never printed."""

    kra_pin: str = ""
    mpesa_paybill: str = ""
    mpesa_account: str = ""
    mpesa_till: str = ""
    bank_name: str = ""
    bank_account_name: str = ""
    bank_account_number: str = ""
    bank_branch: str = ""


@dataclass
class DocumentView:
    doc_type: str  # INV, RCP, QTN, CN
    number: str
    issued: date
    bill_to: BillTo
    lines: list[DocLine]
    due: date | None = None  # invoice due date, or quotation valid-until
    void: bool = False
    paid: bool = False
    payment_method: str = ""
    payment_reference: str = ""
    amount_paid: int | None = None
    settles: str = ""  # invoice number(s) a receipt pays or a credit note corrects
    etims_number: str = ""
    vat_percent: int = VAT_PERCENT
    business: Business = field(default_factory=Business)


def kes(amount: int) -> str:
    return f"{amount:,}" if amount >= 0 else f"-{-amount:,}"


def day(d: date | None) -> str:
    return f"{d.day} {d:%b %Y}" if d else ""


def _meta(v: DocumentView) -> list[tuple[str, str]]:
    title = TITLES[v.doc_type]
    rows = [(f"{title} No", v.number)]
    if v.doc_type == "RCP":
        rows += [
            ("Date paid", day(v.issued)),
            ("For invoice", v.settles),
            ("Paid by", v.payment_method),
            ("Reference", v.payment_reference),
        ]
    elif v.doc_type == "QTN":
        rows += [("Date issued", day(v.issued)), ("Valid until", day(v.due))]
    elif v.doc_type == "CN":
        rows += [("Date issued", day(v.issued)), ("Against invoice", v.settles)]
    else:
        rows += [("Date issued", day(v.issued)), ("Due date", day(v.due))]
    if v.etims_number:
        rows.append(("eTIMS No", v.etims_number))
    return [(label, value) for label, value in rows if value]


def _base(business: Business) -> dict:
    return {"biz": business, "assets": ASSETS.as_uri()}


def build_context(v: DocumentView) -> dict:
    if v.doc_type not in TITLES:
        raise ValueError(f"Unknown document type: {v.doc_type}")
    rows, subtotal, vat = [], 0, 0
    for i, line in enumerate(v.lines, start=1):
        amount = line_amount(line.qty, line.unit_price)
        subtotal += amount
        vat += line_vat(amount, line.vat_exempt, v.vat_percent)
        rows.append(
            {
                "n": i,
                "description": line.description,
                "qty": kes(line.qty),
                "unit_price": kes(line.unit_price),
                "amount": kes(amount),
            }
        )
    total = subtotal + vat
    band = v.amount_paid if v.doc_type == "RCP" and v.amount_paid is not None else total
    return {
        **_base(v.business),
        "title": TITLES[v.doc_type].upper(),
        "number": v.number,
        "meta": _meta(v),
        "bill_to": v.bill_to,
        "rows": rows,
        "subtotal": kes(subtotal),
        "vat": kes(vat),
        "vat_percent": v.vat_percent,
        "show_vat": any(not line.vat_exempt for line in v.lines),
        "total": kes(total),
        "doc_total_row": band != total,  # receipt for a partial payment
        "band_label": TOTAL_LABELS[v.doc_type],
        "band_total": kes(band),
        "stamp": "VOID" if v.void else ("PAID" if v.paid or v.doc_type == "RCP" else ""),
    }


def _html_to_pdf(html: str) -> bytes:
    from weasyprint import HTML  # heavy import; only load when a PDF is made
    from weasyprint.urls import URLFetcher

    # Only our own font and image files; text typed by users can never make the server fetch a URL.
    return HTML(
        string=html, base_url=str(ASSETS), url_fetcher=URLFetcher(allowed_protocols={"file", "data"})
    ).write_pdf()


def render_document_html(v: DocumentView) -> str:
    return render_to_string("ledger/document.html", build_context(v))


def render_document_pdf(v: DocumentView) -> bytes:
    return _html_to_pdf(render_document_html(v))


# ---------- from database records ----------


def business_from_settings() -> Business:
    from .models import BusinessSettings

    s = BusinessSettings.load()
    return Business(
        kra_pin=s.kra_pin,
        mpesa_paybill=s.mpesa_paybill,
        mpesa_account=s.mpesa_account,
        mpesa_till=s.mpesa_till,
        bank_name=s.bank_name,
        bank_branch=s.bank_branch,
        bank_account_name=s.bank_account_name,
        bank_account_number=s.bank_account_number,
    )


def bill_to_for(customer) -> BillTo:
    from .validators import display_ke_phone

    return BillTo(
        name=customer.name,
        phone=display_ke_phone(customer.phone),
        email=customer.email,
        address=customer.address,
        kra_pin=customer.kra_pin,
    )


def view_for(doc) -> DocumentView:
    """DocumentView for a saved Document. Lines are the stored ones, so a reprint never changes."""
    settles, method, reference, amount_paid = "", "", "", None
    paid = False
    if doc.doc_type == "RCP" and doc.payment_id:
        pay = doc.payment
        settles = ", ".join(a.invoice.number for a in pay.allocations.select_related("invoice").order_by("id"))
        method, reference, amount_paid = pay.get_method_display(), pay.reference, doc.total
    elif doc.doc_type == "CN" and doc.related_id:
        settles = doc.related.number
    elif doc.doc_type == "INV" and not doc.void:
        paid = doc.balance() == 0 and doc.paid_amount() > 0
    return DocumentView(
        doc_type=doc.doc_type,
        number=doc.number,
        issued=doc.issued_on,
        bill_to=bill_to_for(doc.customer),
        lines=[DocLine(ln.description, ln.qty, ln.unit_price, ln.vat_exempt) for ln in doc.lines.all()],
        due=doc.due_on,
        void=doc.void,
        paid=paid,
        payment_method=method,
        payment_reference=reference,
        amount_paid=amount_paid,
        settles=settles,
        etims_number=doc.etims_number,
        vat_percent=doc.vat_percent,
        business=business_from_settings(),
    )


def document_pdf(doc) -> bytes:
    return render_document_pdf(view_for(doc))


def statement_entries(customer, start: date, end: date):
    """Rows (date, ref, details, charged, paid) inside the period, plus the balance before it.

    Balance = invoices - credit notes - money received + money refunded. This equals what
    services.customer_balance() reports as owed minus credit.
    """
    from .models import DocType, Document, Payment, Refund

    events = []
    for d in Document.objects.filter(
        customer=customer, void=False, doc_type__in=[DocType.INVOICE, DocType.CREDIT_NOTE]
    ):
        if d.doc_type == DocType.INVOICE:
            events.append((d.issued_on, d.number, f"Invoice, due {day(d.due_on)}", d.total, 0))
        else:
            events.append((d.issued_on, d.number, f"Credit note for {d.related.number}", 0, d.total))
    for p in Payment.objects.filter(customer=customer, void=False).exclude(method=Payment.Method.CREDIT_NOTE):
        ref = p.reference or f"Payment {p.pk}"
        events.append((p.received_on, ref, f"Payment received, {p.get_method_display()}", 0, p.amount))
    for r in Refund.objects.filter(payment__customer=customer, payment__void=False):
        events.append((r.on, r.payment.reference or f"Payment {r.payment_id}", f"Refund: {r.note}", r.amount, 0))
    events.sort(key=lambda e: (e[0], e[1]))
    opening = sum(c - p for (when, _, _, c, p) in events if when < start)
    rows = [e for e in events if start <= e[0] <= end]
    return opening, rows


def statement_pdf(customer, start: date, end: date, unbilled: int = 0) -> bytes:
    from .services import today

    opening, events = statement_entries(customer, start, end)
    running, rows = opening, []
    for when, ref, details, charged, paid in events:
        running += charged - paid
        rows.append(
            {
                "date": day(when),
                "ref": ref,
                "details": details,
                "charged": kes(charged) if charged else "",
                "paid": kes(paid) if paid else "",
                "balance": kes(running),
            }
        )
    ctx = {
        **_base(business_from_settings()),
        "title": "STATEMENT",
        "meta": [("Statement date", day(today())), ("Period", f"{day(start)} to {day(end)}")],
        "bill_to": bill_to_for(customer),
        "opening": kes(opening),
        "rows": rows,
        "closing": kes(running),
        "closing_label": "Balance due (KES)" if running >= 0 else "In your favour (KES)",
        "closing_value": kes(abs(running)),
        "unbilled": kes(unbilled) if unbilled else "",
    }
    return _html_to_pdf(render_to_string("ledger/statement.html", ctx))
