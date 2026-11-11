from datetime import date

import pytest

from ledger.money import (
    Line,
    allocate_payment,
    buy_suggestion,
    check_take_out,
    document_totals,
    format_number,
    line_vat,
    reminder_dates,
    stock_on_hand,
)


@pytest.mark.parametrize(
    ("amount", "vat"),
    [
        (17998, 2880),  # 2879.68 rounds up
        (1003, 160),  # 160.48 rounds down
        (25, 4),  # 4.00 exactly
        (3, 0),  # 0.48 rounds down
        (1, 0),  # 0.16
        (4, 1),  # 0.64
        (0, 0),
    ],
)
def test_line_vat_rounds_to_whole_shilling(amount, vat):
    assert line_vat(amount, vat_exempt=False) == vat


def test_line_vat_rounding_boundary():
    # Whole-shilling amounts never give VAT ending in exactly .50, so test either side of it.
    assert line_vat(103, vat_exempt=False) == 16  # 16.48
    assert line_vat(97, vat_exempt=False) == 16  # 15.52


def test_exempt_line_has_no_vat():
    assert line_vat(10_000, vat_exempt=True) == 0


def test_vat_is_rounded_per_line_not_on_total():
    lines = [Line(10, 650), Line(20, 1150), Line(2, 8999), Line(50, 45, vat_exempt=True)]
    t = document_totals(lines)
    assert t.subtotal == 49_748
    assert t.vat == 1040 + 3680 + 2880
    assert t.total == t.subtotal + t.vat == 57_348
    assert t.show_vat_row is True


def test_per_line_rounding_differs_from_total_rounding():
    # Three lines of 3 KES: per line VAT 0.48 -> 0 each; on the total 9 x 16% = 1.44 -> 1.
    t = document_totals([Line(1, 3), Line(1, 3), Line(1, 3)])
    assert t.vat == 0
    assert t.total == 9


def test_no_vat_row_when_every_line_is_exempt():
    t = document_totals([Line(50, 45, vat_exempt=True)])
    assert (t.vat, t.total, t.show_vat_row) == (0, 2250, False)


@pytest.mark.parametrize(("qty", "price"), [(0, 100), (-1, 100), (1, -5)])
def test_bad_lines_rejected(qty, price):
    with pytest.raises(ValueError):
        document_totals([Line(qty, price)])


def test_payment_allocation_oldest_first_and_reconciles():
    allocations, over = allocate_payment(15_000, [(1, 10_000), (2, 5_000)], allow_partial=False)
    assert [(a.invoice_id, a.amount) for a in allocations] == [(1, 10_000), (2, 5_000)]
    assert over == 0
    assert sum(a.amount for a in allocations) + over == 15_000


def test_overpayment_is_returned_for_refund_or_credit():
    allocations, over = allocate_payment(12_500, [(1, 10_000)], allow_partial=False)
    assert allocations[0].amount == 10_000
    assert over == 2_500
    assert sum(a.amount for a in allocations) + over == 12_500


def test_partial_payment_blocked_by_default():
    with pytest.raises(ValueError, match="Partial payments are off"):
        allocate_payment(4_000, [(1, 10_000)], allow_partial=False)


def test_partial_payment_when_allowed():
    allocations, over = allocate_payment(14_000, [(1, 10_000), (2, 9_000)], allow_partial=True)
    assert [(a.invoice_id, a.amount) for a in allocations] == [(1, 10_000), (2, 4_000)]
    assert over == 0
    balances_after = {1: 10_000 - 10_000, 2: 9_000 - 4_000}
    assert balances_after == {1: 0, 2: 5_000}


@pytest.mark.parametrize("amount", [0, -100])
def test_payment_must_be_positive(amount):
    with pytest.raises(ValueError):
        allocate_payment(amount, [(1, 100)], allow_partial=True)


def test_reminder_dates():
    r = reminder_dates(date(2026, 12, 1))
    assert r == {
        "before_3": date(2026, 11, 28),
        "due": date(2026, 12, 1),
        "after_7": date(2026, 12, 8),
    }


def test_reminder_dates_cross_year():
    assert reminder_dates(date(2026, 12, 28))["after_7"] == date(2027, 1, 4)


def test_number_format():
    assert format_number("INV", 2026, 1) == "ESI-INV-2026-0001"
    assert format_number("CN", 2026, 12) == "ESI-CN-2026-0012"
    assert format_number("RCP", 2026, 12345) == "ESI-RCP-2026-12345"


@pytest.mark.parametrize(("t", "seq"), [("XYZ", 1), ("INV", 0)])
def test_number_format_rejects_bad_input(t, seq):
    with pytest.raises(ValueError):
        format_number(t, 2026, seq)


def test_stock_is_sum_of_movements():
    assert stock_on_hand([20, -5, 10, -3]) == 22


def test_sale_over_stock_blocked_with_count():
    with pytest.raises(ValueError, match="Only 4 left in stock"):
        check_take_out(on_hand=4, qty=5)
    check_take_out(on_hand=4, qty=4)  # exactly what is left is fine


def test_buy_list():
    assert buy_suggestion(reorder_level=10, on_hand=11, sold_last_3_months=90) is None
    item = buy_suggestion(reorder_level=10, on_hand=4, sold_last_3_months=31)
    assert item.target == 10 + 11  # 31 / 3 = 10.33 -> 11, never under-order
    assert item.order_qty == 17
    assert item.used_history is True


def test_buy_list_without_history_uses_reorder_level():
    item = buy_suggestion(reorder_level=10, on_hand=10, sold_last_3_months=0)
    assert (item.target, item.order_qty, item.used_history) == (10, 0, False)
