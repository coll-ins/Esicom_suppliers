"""Render invoices, receipts, quotations and credit notes to A4 PDF (WeasyPrint)."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from django.template.loader import render_to_string

from .money import line_amount, line_vat

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
    settles: str = ""  # invoice number a receipt pays or a credit note corrects
    etims_number: str = ""
    business: Business = field(default_factory=Business)


def kes(amount: int) -> str:
    return f"{amount:,}"


def _day(d: date | None) -> str:
    return f"{d.day} {d:%b %Y}" if d else ""


def _meta(v: DocumentView) -> list[tuple[str, str]]:
    title = TITLES[v.doc_type]
    rows = [(f"{title} No", v.number)]
    if v.doc_type == "RCP":
        rows += [
            ("Date paid", _day(v.issued)),
            ("For invoice", v.settles),
            ("Paid by", v.payment_method),
            ("Reference", v.payment_reference),
        ]
    elif v.doc_type == "QTN":
        rows += [("Date issued", _day(v.issued)), ("Valid until", _day(v.due))]
    elif v.doc_type == "CN":
        rows += [("Date issued", _day(v.issued)), ("Against invoice", v.settles)]
    else:
        rows += [("Date issued", _day(v.issued)), ("Due date", _day(v.due))]
    if v.etims_number:
        rows.append(("eTIMS No", v.etims_number))
    return [(label, value) for label, value in rows if value]


def build_context(v: DocumentView) -> dict:
    if v.doc_type not in TITLES:
        raise ValueError(f"Unknown document type: {v.doc_type}")
    rows, subtotal, vat = [], 0, 0
    for i, line in enumerate(v.lines, start=1):
        amount = line_amount(line.qty, line.unit_price)
        subtotal += amount
        vat += line_vat(amount, line.vat_exempt)
        rows.append({
            "n": i,
            "description": line.description,
            "qty": kes(line.qty),
            "unit_price": kes(line.unit_price),
            "amount": kes(amount),
        })
    total = subtotal + vat
    band = v.amount_paid if v.doc_type == "RCP" and v.amount_paid is not None else total
    return {
        "title": TITLES[v.doc_type].upper(),
        "meta": _meta(v),
        "bill_to": v.bill_to,
        "rows": rows,
        "subtotal": kes(subtotal),
        "vat": kes(vat),
        "show_vat": any(not line.vat_exempt for line in v.lines),
        "total": kes(total),
        "doc_total_row": band != total,  # receipt for a partial payment
        "band_label": TOTAL_LABELS[v.doc_type],
        "band_total": kes(band),
        "stamp": "VOID" if v.void else ("PAID" if v.paid or v.doc_type == "RCP" else ""),
        "biz": v.business,
        "assets": ASSETS.as_uri(),
    }


def render_document_html(v: DocumentView) -> str:
    return render_to_string("ledger/document.html", build_context(v))


def render_document_pdf(v: DocumentView) -> bytes:
    from weasyprint import HTML  # heavy import; only load when a PDF is made

    return HTML(string=render_document_html(v), base_url=str(ASSETS)).write_pdf()
