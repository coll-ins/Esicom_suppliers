from datetime import date
from io import BytesIO

from pypdf import PdfReader

from ledger.pdf import (
    BillTo,
    Business,
    DocLine,
    DocumentView,
    render_document_html,
    render_document_pdf,
)

LINES = [DocLine("A4 printing paper (ream)", 10, 450), DocLine("HP toner cartridge 85A", 2, 5500)]


def _text(pdf: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)


def test_invoice_pdf_contains_correct_total():
    v = DocumentView(
        "INV", "ESI-INV-2026-0001", date(2026, 11, 11), BillTo("Sample Customer Ltd"), LINES, due=date(2026, 11, 25)
    )
    text = _text(render_document_pdf(v))
    # 4,500 + 11,000 = 15,500; VAT 720 + 1,760 = 2,480; total 17,980
    assert "INVOICE" in text
    assert "ESI-INV-2026-0001" in text
    assert "15,500" in text and "2,480" in text and "17,980" in text
    assert "VAT (16%)" in text


def test_no_vat_row_and_no_blank_settings_printed():
    v = DocumentView(
        "INV",
        "ESI-INV-2026-0002",
        date(2026, 11, 11),
        BillTo("X"),
        [DocLine("Exercise books", 50, 45, vat_exempt=True)],
    )
    html = render_document_html(v)
    assert "VAT (16%)" not in html
    assert "KRA PIN" not in html
    assert "Paybill" not in html and "Account" not in html


def test_settings_printed_when_filled():
    biz = Business(kra_pin="P000000000A", mpesa_paybill="123456", mpesa_account="INV")
    v = DocumentView("INV", "ESI-INV-2026-0003", date(2026, 11, 11), BillTo("X"), LINES, business=biz)
    html = render_document_html(v)
    assert "P000000000A" in html and "Paybill 123456" in html


def test_receipt_shows_paid_mark_and_partial_amount():
    v = DocumentView(
        "RCP",
        "ESI-RCP-2026-0001",
        date(2026, 11, 12),
        BillTo("X"),
        LINES,
        amount_paid=10_000,
        payment_method="M-Pesa",
        payment_reference="TKB7XY12AB",
        settles="ESI-INV-2026-0001",
    )
    text = _text(render_document_pdf(v))
    assert "RECEIPT" in text and "PAID" in text
    assert "10,000" in text and "17,980" in text  # amount paid and the invoice total
    assert "ESI-INV-2026-0001" in text and "TKB7XY12AB" in text


def test_void_mark():
    v = DocumentView("INV", "ESI-INV-2026-0004", date(2026, 11, 11), BillTo("X"), LINES, void=True)
    assert "VOID" in _text(render_document_pdf(v))
