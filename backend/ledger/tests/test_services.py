from datetime import timedelta
from unittest import mock

import pytest
from django.core import mail
from django.db import connection
from django.test.utils import CaptureQueriesContext

from ledger import jobs, services
from ledger.models import (
    Alert,
    BusinessSettings,
    Document,
    Payment,
    ReminderSent,
    Sequence,
    StockMovement,
)
from ledger.pdf import statement_entries
from ledger.services import LedgerError

from .conftest import custom, item

pytestmark = pytest.mark.django_db


def reconcile(customer):
    """Totals and balances must agree from every direction."""
    for p in Payment.objects.filter(customer=customer, void=False):
        assert p.allocated() + p.refunded + p.unallocated() == p.amount
        assert p.unallocated() >= 0
        assert sum(r.amount for r in p.refunds.all()) == p.refunded
    for inv in Document.objects.filter(customer=customer, doc_type="INV", void=False):
        assert inv.balance() == inv.total - inv.paid_amount() - inv.credited_amount()
        assert inv.balance() >= 0
    bal = services.customer_balance(customer)
    opening, rows = statement_entries(
        customer, services.today() - timedelta(days=3650), services.today() + timedelta(days=1)
    )
    statement_balance = opening + sum(c - p for (_, _, _, c, p) in rows)
    assert statement_balance == bal["owed"] - bal["credit"]
    assert services.balances_for([customer.pk])[customer.pk] == bal


# ---------- invoices and VAT ----------


def test_sale_issues_invoice_with_per_line_vat(owner, customer, paper, books):
    r = services.record_sale(owner, customer, [item(paper, 3), item(books, 10), custom("Branded polo", 20, 1150)])
    inv = r.invoice
    assert inv.number.startswith("ESI-INV-") and inv.number.endswith("-0001")
    # paper 1950 -> VAT 312; books exempt 450; polo 23000 -> VAT 3680
    assert (inv.subtotal, inv.vat, inv.total) == (1950 + 450 + 23000, 312 + 3680, 1950 + 450 + 23000 + 312 + 3680)
    assert [ln.vat for ln in inv.lines.all()] == [312, 0, 3680]
    assert paper.on_hand() == 17 and books.on_hand() == 90
    reconcile(customer)


def test_custom_job_lines_do_not_touch_stock(owner, customer):
    services.record_sale(owner, customer, [custom("Branded polo x20", 1, 23000)])
    assert StockMovement.objects.count() == 0


def test_sale_over_stock_is_blocked_with_count_and_nothing_saved(owner, customer, paper):
    with pytest.raises(LedgerError, match="only 20 left"):
        services.record_sale(owner, customer, [item(paper, 15), item(paper, 6)])  # same product twice
    assert paper.on_hand() == 20
    assert Document.objects.count() == 0 and Sequence.objects.count() == 0


def test_stock_never_negative_on_take_out(owner, paper):
    with pytest.raises(LedgerError, match="Only 20 left"):
        services.take_out_stock(owner, paper, 21, "Damaged")
    services.take_out_stock(owner, paper, 20, "Damaged")
    assert paper.on_hand() == 0
    with pytest.raises(LedgerError):
        services.take_out_stock(owner, paper, 1, "Damaged")


def test_stock_is_sum_of_movements(owner, paper):
    services.receive_stock(owner, paper, 10, unit_cost=480)
    services.take_out_stock(owner, paper, 4, "Office use")
    assert paper.on_hand() == 20 + 10 - 4 == sum(paper.movements.values_list("qty", flat=True))


# ---------- numbering ----------


def test_numbering_has_no_gaps_and_never_reuses(owner, customer, paper):
    services.record_sale(owner, customer, [item(paper, 1)])
    with pytest.raises(LedgerError):
        services.record_sale(owner, customer, [item(paper, 999)])  # fails: number must not be used up
    r = services.record_sale(owner, customer, [item(paper, 1)])
    services.void_document(owner, r.invoice, "Mistake")
    r3 = services.record_sale(owner, customer, [item(paper, 1)])
    numbers = list(Document.objects.filter(doc_type="INV").order_by("seq").values_list("number", flat=True))
    year = services.today().year
    assert numbers == [f"ESI-INV-{year}-0001", f"ESI-INV-{year}-0002", f"ESI-INV-{year}-0003"]
    assert Document.objects.get(number=f"ESI-INV-{year}-0002").void  # voided keeps its number
    assert r3.invoice.seq == 3


def test_each_type_has_its_own_sequence(owner, customer, paper):
    r = services.record_sale(owner, customer, [item(paper, 1)], payment={"amount": 754, "method": "cash"})
    receipt = services.make_receipt(owner, r.payment)
    qtn = services.create_quotation(owner, customer, [item(paper, 1)])
    year = services.today().year
    assert receipt.number == f"ESI-RCP-{year}-0001"
    assert qtn.number == f"ESI-QTN-{year}-0001"


# ---------- tabs ----------


def test_running_tab_bills_only_unbilled_items_and_stays_open(owner, tab_customer, paper):
    r = services.record_sale(owner, tab_customer, [item(paper, 2)])
    assert r.invoice is None and r.tab is not None
    inv1 = services.bill_tab(owner, tab_customer)
    assert inv1.total == 1300 + 208
    services.record_sale(owner, tab_customer, [item(paper, 1)])
    inv2 = services.bill_tab(owner, tab_customer)
    assert inv2.lines.count() == 1 and inv2.total == 650 + 104
    with pytest.raises(LedgerError, match="Nothing new to bill"):
        services.bill_tab(owner, tab_customer)
    assert tab_customer.tabs.filter(closed_at__isnull=True).count() == 1
    reconcile(tab_customer)


def test_closing_tab_finalises_unbilled_items(owner, tab_customer, paper):
    services.record_sale(owner, tab_customer, [item(paper, 2)])
    final = services.bill_tab(owner, tab_customer, close=True)
    assert final.is_final and final.total == 1508
    assert not tab_customer.tabs.filter(closed_at__isnull=True).exists()
    services.record_sale(owner, tab_customer, [item(paper, 1)])  # a new tab opens by itself
    assert tab_customer.tabs.filter(closed_at__isnull=True).count() == 1


def test_removing_tab_item_restores_stock(owner, tab_customer, paper):
    services.record_sale(owner, tab_customer, [item(paper, 5)])
    line = tab_customer.sale_lines.get()
    services.remove_tab_line(owner, line, "Wrong item")
    assert paper.on_hand() == 20
    with pytest.raises(LedgerError, match="Nothing new to bill"):
        services.bill_tab(owner, tab_customer)


# ---------- payments ----------


def test_cash_sale_marks_invoice_paid(owner, customer, paper):
    r = services.record_sale(owner, customer, [item(paper, 1)], payment={"amount": 754, "method": "cash"})
    assert r.invoice.balance() == 0 and r.invoice.due_on == services.today()
    assert Document.objects.filter(doc_type="RCP").count() == 0  # receipt only when asked
    reconcile(customer)


def test_partial_payment_blocked_by_default_and_allowed_by_owner_setting(owner, customer, paper):
    inv = services.record_sale(owner, customer, [item(paper, 2)]).invoice  # 1508
    with pytest.raises(LedgerError, match="Partial payments are off"):
        services.record_payment(owner, customer, amount=1000, method="cash")
    inv.allow_partial = True
    inv.save()
    services.record_payment(owner, customer, amount=1000, method="cash")
    assert inv.balance() == 508
    reconcile(customer)


def test_overpayment_refund_is_default_and_credit_is_used_on_next_invoice(owner, customer, paper):
    inv = services.record_sale(owner, customer, [item(paper, 1)]).invoice  # 754
    p, extra = services.record_payment(owner, customer, amount=1000, method="mpesa", reference="ABC")
    assert extra == 246 and p.refunded == 246 and p.unallocated() == 0
    inv2 = services.record_sale(owner, customer, [item(paper, 1)]).invoice
    p2, extra2 = services.record_payment(owner, customer, amount=1000, method="cash", overpay="credit")
    assert extra2 == 246 and p2.unallocated() == 246 and inv2.balance() == 0
    inv3 = services.record_sale(owner, customer, [item(paper, 1)]).invoice
    assert inv3.balance() == 754 - 246  # credit applied automatically
    assert inv.balance() == 0
    reconcile(customer)


def test_payment_allocates_oldest_first(owner, customer, paper):
    customer.allow_partial = True
    customer.save()
    a = services.record_sale(owner, customer, [item(paper, 1)]).invoice
    b = services.record_sale(owner, customer, [item(paper, 1)]).invoice
    services.record_payment(owner, customer, amount=1000, method="cash")
    assert a.balance() == 0 and b.balance() == 754 - 246
    reconcile(customer)


def test_void_payment_reopens_invoice(owner, customer, paper):
    inv = services.record_sale(owner, customer, [item(paper, 1)]).invoice
    p, _ = services.record_payment(owner, customer, amount=754, method="cash")
    receipt = services.make_receipt(owner, p)
    services.void_payment(owner, p, "Bounced")
    assert inv.balance() == 754
    receipt.refresh_from_db()
    assert receipt.void
    reconcile(customer)


def test_receipt_contents(owner, customer, paper):
    inv = services.record_sale(owner, customer, [item(paper, 1)]).invoice
    p, _ = services.record_payment(owner, customer, amount=1000, method="cash", overpay="credit")
    r = services.make_receipt(owner, p)
    assert r.total == 1000 and r.vat == 0
    assert [ln.description for ln in r.lines.all()] == [
        f"Payment for invoice {inv.number}",
        "Kept as credit for the next invoice",
    ]
    assert services.make_receipt(owner, p) == r  # asking twice returns the same receipt


def test_refund_credit(owner, customer, paper):
    services.record_payment(owner, customer, amount=500, method="cash", overpay="credit")
    with pytest.raises(LedgerError, match="only has KES 500"):
        services.refund_credit(owner, customer, 600, "Cash")
    services.refund_credit(owner, customer, 200, "Cash back")
    assert services.customer_balance(customer)["credit"] == 300
    reconcile(customer)


# ---------- voids and credit notes ----------


def test_void_restores_stock_and_keeps_paid_money_as_credit(owner, customer, paper):
    r = services.record_sale(owner, customer, [item(paper, 4)], payment={"amount": 3016, "method": "cash"})
    services.void_document(owner, r.invoice, "Customer cancelled")
    assert paper.on_hand() == 20
    r.invoice.refresh_from_db()
    assert r.invoice.void and r.invoice.balance() == 0
    assert services.customer_balance(customer)["credit"] == 3016
    with pytest.raises(LedgerError, match="already void"):
        services.void_document(owner, r.invoice, "again")
    reconcile(customer)


def test_staff_cannot_void_unless_owner_allows(owner, staff, customer, paper):
    inv = services.record_sale(staff, customer, [item(paper, 1)]).invoice
    with pytest.raises(LedgerError, match="Only the owner"):
        services.void_document(staff, inv, "x")
    s = BusinessSettings.load()
    s.staff_can_void = True
    s.save()
    services.void_document(staff, inv, "Allowed now")
    inv.refresh_from_db()
    assert inv.void


def test_credit_note_reduces_balance_and_restocks(owner, customer, paper):
    inv = services.record_sale(owner, customer, [item(paper, 4)]).invoice  # 3016
    cn = services.credit_note(owner, inv, [_restock(item(paper, 1))], "Damaged ream")
    assert cn.number.startswith("ESI-CN-") and cn.total == 754
    assert inv.balance() == 3016 - 754 and paper.on_hand() == 17
    with pytest.raises(LedgerError, match="only return items this invoice sold"):
        services.credit_note(owner, inv, [_restock(item(paper, 4, price=1))], "too many")
    reconcile(customer)


def test_credit_note_on_paid_invoice_refunds_or_credits(owner, customer, paper):
    inv = services.record_sale(owner, customer, [item(paper, 2)], payment={"amount": 1508, "method": "cash"}).invoice
    services.credit_note(owner, inv, [custom("Discount", 1, 100)], "Discount", overpay="credit")
    assert services.customer_balance(customer)["credit"] == 116
    services.credit_note(owner, inv, [custom("Discount", 1, 100)], "Discount 2")
    assert services.customer_balance(customer)["credit"] == 116  # second one refunded
    with pytest.raises(LedgerError, match="cannot be more than"):
        services.credit_note(owner, inv, [custom("Too much", 1, 2000)], "x")
    reconcile(customer)


def test_void_invoice_with_credit_notes_blocked(owner, customer, paper):
    inv = services.record_sale(owner, customer, [item(paper, 1)]).invoice
    cn = services.credit_note(owner, inv, [custom("Discount", 1, 50)], "Discount")
    with pytest.raises(LedgerError, match="Void them first"):
        services.void_document(owner, inv, "x")
    services.void_document(owner, cn, "Wrong")
    services.void_document(owner, inv, "Now fine")
    reconcile(customer)


def _restock(it):
    it.restock = True
    return it


# ---------- quotations ----------


def test_quotation_does_not_touch_stock_and_converts_once(owner, customer, paper):
    qtn = services.create_quotation(owner, customer, [item(paper, 5)])
    assert paper.on_hand() == 20
    r = services.convert_quotation(owner, qtn)
    assert r.invoice.related == qtn and paper.on_hand() == 15
    with pytest.raises(LedgerError, match="already has an invoice"):
        services.convert_quotation(owner, qtn)


def test_tab_customer_quotation_converts_to_invoice_not_tab(owner, tab_customer, paper):
    qtn = services.create_quotation(owner, tab_customer, [item(paper, 1)])
    assert services.convert_quotation(owner, qtn).invoice is not None


# ---------- credit limit ----------


def test_credit_limit_alerts_owner_and_staff_once(owner, staff, customer, paper, django_capture_on_commit_callbacks):
    customer.credit_limit = 1000
    customer.save()
    with django_capture_on_commit_callbacks(execute=True):
        services.record_sale(owner, customer, [item(paper, 1)])  # 754, under
        services.record_sale(owner, customer, [item(paper, 1)])  # 1508, over
        services.record_sale(owner, customer, [item(paper, 1)])  # still over: no second alert
    assert Alert.objects.filter(kind="credit_limit").count() == 1
    assert len(mail.outbox) == 1
    assert set(mail.outbox[0].to) == {"owner@example.com", "staff@example.com"}
    services.record_payment(owner, customer, amount=2262, method="cash")
    assert not Alert.objects.filter(resolved=False).exists()


def test_walk_in_must_pay_now(owner, paper):
    with pytest.raises(LedgerError, match="Walk-in"):
        services.record_sale(owner, services.walk_in_customer(), [item(paper, 1)])


# ---------- reminders ----------


def _invoice_due(owner, customer, paper, due):
    return services.record_sale(owner, customer, [item(paper, 1)], due_on=due).invoice


def test_reminder_dates_send_on_the_right_days(owner, customer, paper):
    today = services.today()
    inv = _invoice_due(owner, customer, paper, today + timedelta(days=3))
    assert jobs.send_due_reminders(today)["sent"] == 1
    assert ReminderSent.objects.get(invoice=inv).kind == "before_3"
    assert jobs.send_due_reminders(today)["sent"] == 0  # once only
    assert jobs.send_due_reminders(today + timedelta(days=3))["sent"] == 1
    assert jobs.send_due_reminders(today + timedelta(days=4))["sent"] == 0
    assert jobs.send_due_reminders(today + timedelta(days=10))["sent"] == 1
    assert sorted(ReminderSent.objects.filter(skipped=False).values_list("kind", flat=True)) == [
        "after_7",
        "before_3",
        "due",
    ]
    assert len(mail.outbox) == 3 and mail.outbox[0].attachments[0][0] == f"{inv.number}.pdf"


def test_missed_reminders_are_skipped_not_sent_late(owner, customer, paper):
    today = services.today()
    _invoice_due(owner, customer, paper, today - timedelta(days=1))  # server slept through two dates
    assert jobs.send_due_reminders(today) == {"sent": 0, "skipped": 2}
    assert len(mail.outbox) == 0


def test_paid_invoices_get_no_reminders(owner, customer, paper):
    today = services.today()
    _invoice_due(owner, customer, paper, today)
    services.record_payment(owner, customer, amount=754, method="cash")
    assert jobs.send_due_reminders(today)["sent"] == 0


def test_daily_jobs_run_once_per_day(owner):
    with mock.patch("ledger.jobs.send_due_reminders", return_value={"sent": 0, "skipped": 0}) as m:
        assert jobs.run_daily_jobs(services.today()) is not None
        assert jobs.run_daily_jobs(services.today()) is None
    assert m.call_count == 1


# ---------- speed ----------


def test_customer_balances_take_constant_queries(owner, paper):
    from ledger.models import Customer

    ids = []
    for n in range(15):
        c = Customer.objects.create(name=f"Customer {n}")
        services.record_sale(owner, c, [custom("Job", 1, 100)])
        ids.append(c.pk)
    with CaptureQueriesContext(connection) as ctx:
        services.balances_for(ids)
    assert len(ctx.captured_queries) <= 5


def test_same_mpesa_code_cannot_be_recorded_twice(owner, customer, paper):
    services.record_sale(
        owner, customer, [item(paper, 1)], payment={"amount": 754, "method": "mpesa", "reference": "TKB7XY12AB"}
    )
    with pytest.raises(LedgerError, match="already recorded"):
        services.record_payment(owner, customer, amount=100, method="mpesa", reference="tkb7xy12ab", overpay="credit")
    assert Document.objects.filter(doc_type="INV").count() == 1
