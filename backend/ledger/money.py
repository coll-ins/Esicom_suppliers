"""Money rules for the ledger. All amounts are whole Kenyan shillings (int)."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

VAT_PERCENT = 16


def line_amount(qty: int, unit_price: int) -> int:
    if qty < 1:
        raise ValueError("Quantity must be at least 1.")
    if unit_price < 0:
        raise ValueError("Unit price cannot be negative.")
    return qty * unit_price


def line_vat(amount: int, vat_exempt: bool) -> int:
    """VAT for one line, rounded to the whole shilling (half up)."""
    if vat_exempt:
        return 0
    return int((Decimal(amount) * VAT_PERCENT / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Line:
    qty: int
    unit_price: int
    vat_exempt: bool = False


@dataclass(frozen=True)
class Totals:
    subtotal: int  # excluding VAT
    vat: int
    total: int  # what the customer pays
    show_vat_row: bool  # documents show a VAT row only when a line is VAT-able


def document_totals(lines: list[Line]) -> Totals:
    subtotal = vat = 0
    for line in lines:
        amount = line_amount(line.qty, line.unit_price)
        subtotal += amount
        vat += line_vat(amount, line.vat_exempt)
    return Totals(subtotal, vat, subtotal + vat, any(not line.vat_exempt for line in lines))


@dataclass(frozen=True)
class Allocation:
    invoice_id: int
    amount: int


def allocate_payment(amount: int, open_invoices: list[tuple[int, int]], allow_partial: bool):
    """Apply a payment to open invoices, oldest first.

    open_invoices: [(invoice_id, balance_due)] oldest first.
    Returns (allocations, overpayment). Overpayment is what is left after every
    open invoice is paid; the caller refunds it or keeps it as credit.
    Without partial payments, each invoice must be paid in full.
    """
    if amount <= 0:
        raise ValueError("Payment must be more than 0 KES.")
    allocations: list[Allocation] = []
    remaining = amount
    for invoice_id, balance in open_invoices:
        if remaining == 0:
            break
        if remaining >= balance:
            allocations.append(Allocation(invoice_id, balance))
            remaining -= balance
        elif allow_partial:
            allocations.append(Allocation(invoice_id, remaining))
            remaining = 0
        else:
            raise ValueError(
                f"KES {remaining:,} is not enough to clear the balance of KES {balance:,}. "
                "Partial payments are off for this customer."
            )
    return allocations, remaining


def reminder_dates(due: date) -> dict[str, date]:
    """Due-date emails: 3 days before, on the due date, 7 days after."""
    return {
        "before_3": due - timedelta(days=3),
        "due": due,
        "after_7": due + timedelta(days=7),
    }


def format_number(doc_type: str, year: int, seq: int) -> str:
    """ESI-INV-2026-0001. doc_type: INV, RCP, QTN or CN."""
    if doc_type not in {"INV", "RCP", "QTN", "CN"}:
        raise ValueError(f"Unknown document type: {doc_type}")
    if seq < 1:
        raise ValueError("Sequence starts at 1.")
    return f"ESI-{doc_type}-{year}-{seq:04d}"


def stock_on_hand(movement_qtys: list[int]) -> int:
    """Stock = sum of signed movements. Ins are positive, takes out are negative."""
    return sum(movement_qtys)


def check_take_out(on_hand: int, qty: int) -> None:
    if qty < 1:
        raise ValueError("Quantity must be at least 1.")
    if qty > on_hand:
        raise ValueError(f"Only {on_hand} left in stock. You cannot sell {qty}.")


@dataclass(frozen=True)
class BuyItem:
    target: int
    order_qty: int
    used_history: bool


def buy_suggestion(reorder_level: int, on_hand: int, sold_last_3_months: int) -> BuyItem | None:
    """Target = reorder level + average monthly sales. None when stock is above reorder level."""
    if on_hand > reorder_level:
        return None
    avg_monthly = -(-sold_last_3_months // 3)  # round up so we never under-order
    target = reorder_level + avg_monthly
    return BuyItem(target=target, order_qty=max(target - on_hand, 0), used_history=sold_last_3_months > 0)
