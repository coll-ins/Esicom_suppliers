"""Every change to money or stock goes through here, inside one database transaction.

The customer row is locked (select_for_update) for money changes, and product rows
for stock changes, so two staff saving at once cannot oversell or double-allocate.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.db.models import F, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from . import money
from .models import (
    Alert,
    AuditLog,
    BusinessSettings,
    Customer,
    DocType,
    Document,
    DocumentLine,
    Payment,
    PaymentAllocation,
    Product,
    Refund,
    SaleLine,
    Sequence,
    StockMovement,
    Tab,
)


class LedgerError(Exception):
    """A plain-English reason shown to the user."""


@dataclass
class Item:
    description: str
    qty: int
    unit_price: int
    vat_exempt: bool = False
    product: Product | None = None
    restock: bool = False  # credit notes only


def today() -> date:
    return timezone.localdate()


def walk_in_customer() -> Customer:
    obj, _ = Customer.objects.get_or_create(is_walk_in=True, defaults={"name": "Walk-in customer"})
    return obj


def audit(user, action: str, entity: str, entity_id, summary: str) -> None:
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id or ""),
        summary=summary[:300],
    )


# ---------- queries ----------


def documents_with_balance():
    """Every document, with paid_amt, credited_amt and bal (balance; meaningful for invoices)."""
    paid = (
        PaymentAllocation.objects.filter(invoice=OuterRef("pk")).values("invoice").annotate(t=Sum("amount")).values("t")
    )
    credited = (
        Document.objects.filter(related=OuterRef("pk"), doc_type=DocType.CREDIT_NOTE, void=False)
        .values("related")
        .annotate(t=Sum("credit_applied"))
        .values("t")
    )
    return Document.objects.annotate(
        paid_amt=Coalesce(Subquery(paid), 0), credited_amt=Coalesce(Subquery(credited), 0)
    ).annotate(bal=F("total") - F("paid_amt") - F("credited_amt"))


def invoices_with_balance():
    return documents_with_balance().filter(doc_type=DocType.INVOICE)


def open_invoices(customer):
    return invoices_with_balance().filter(customer=customer, void=False, bal__gt=0).order_by("issued_on", "id")


def payments_with_unallocated():
    allocated = (
        PaymentAllocation.objects.filter(payment=OuterRef("pk")).values("payment").annotate(t=Sum("amount")).values("t")
    )
    return (
        Payment.objects.filter(void=False)
        .annotate(alloc=Coalesce(Subquery(allocated), 0))
        .annotate(free=F("amount") - F("refunded") - F("alloc"))
    )


def unbilled_lines(customer):
    return SaleLine.objects.filter(customer=customer, invoice__isnull=True, voided=False).select_related("product")


def unbilled_total(customer, percent: int | None = None) -> int:
    percent = BusinessSettings.load().vat_percent if percent is None else percent
    lines = [money.Line(sl.qty, sl.unit_price, sl.vat_exempt) for sl in unbilled_lines(customer)]
    return money.document_totals(lines, percent).total if lines else 0


def customer_balance(customer) -> dict:
    owed = open_invoices(customer).aggregate(t=Coalesce(Sum("bal"), 0))["t"]
    credit = (
        payments_with_unallocated().filter(customer=customer, free__gt=0).aggregate(t=Coalesce(Sum("free"), 0))["t"]
    )
    unbilled = unbilled_total(customer)
    return {"owed": owed, "unbilled": unbilled, "credit": credit, "balance": owed + unbilled - credit}


def balances_for(customer_ids) -> dict[int, dict]:
    """customer_balance() for many customers in four queries."""
    ids = list(customer_ids)
    out = {cid: {"owed": 0, "unbilled": 0, "credit": 0, "balance": 0} for cid in ids}
    for row in (
        invoices_with_balance()
        .filter(customer_id__in=ids, void=False, bal__gt=0)
        .values("customer_id")
        .annotate(t=Sum("bal"))
    ):
        out[row["customer_id"]]["owed"] = row["t"]
    for row in (
        payments_with_unallocated()
        .filter(customer_id__in=ids, free__gt=0)
        .values("customer_id")
        .annotate(t=Sum("free"))
    ):
        out[row["customer_id"]]["credit"] = row["t"]
    percent = BusinessSettings.load().vat_percent
    lines = defaultdict(list)
    for sl in SaleLine.objects.filter(customer_id__in=ids, invoice__isnull=True, voided=False):
        lines[sl.customer_id].append(money.Line(sl.qty, sl.unit_price, sl.vat_exempt))
    for cid, ls in lines.items():
        out[cid]["unbilled"] = money.document_totals(ls, percent).total
    for b in out.values():
        b["balance"] = b["owed"] + b["unbilled"] - b["credit"]
    return out


def stock_levels(product_ids) -> dict[int, int]:
    rows = StockMovement.objects.filter(product_id__in=product_ids).values("product_id").annotate(t=Sum("qty"))
    levels = {pid: 0 for pid in product_ids}
    levels.update({r["product_id"]: r["t"] for r in rows})
    return levels


# ---------- numbering ----------


def next_number(doc_type: str, on: date) -> tuple[str, int, int]:
    """Locks the sequence row: numbers are issued in order, never reused, and a failed save
    rolls the counter back with it, so there are no gaps."""
    try:
        seq = Sequence.objects.select_for_update().get(doc_type=doc_type, year=on.year)
    except Sequence.DoesNotExist:
        try:
            with transaction.atomic():
                Sequence.objects.create(doc_type=doc_type, year=on.year)
        except IntegrityError:
            pass  # another request created it first
        seq = Sequence.objects.select_for_update().get(doc_type=doc_type, year=on.year)
    seq.last += 1
    seq.save(update_fields=["last"])
    return money.format_number(doc_type, on.year, seq.last), on.year, seq.last


def _lock_customer(customer) -> Customer:
    return Customer.objects.select_for_update().get(pk=customer.pk)


def _new_document(doc_type, customer, items: list[Item], user, *, issued_on=None, percent=None, **fields) -> Document:
    issued_on = issued_on or today()
    number, year, seq = next_number(doc_type, issued_on)
    percent = BusinessSettings.load().vat_percent if percent is None else percent
    doc = Document.objects.create(
        doc_type=doc_type,
        number=number,
        year=year,
        seq=seq,
        customer=customer,
        issued_on=issued_on,
        vat_percent=percent,
        created_by=user,
        **fields,
    )
    subtotal = vat = 0
    rows = []
    for pos, it in enumerate(items, start=1):
        amount = money.line_amount(it.qty, it.unit_price)
        line_vat = money.line_vat(amount, it.vat_exempt, percent)
        subtotal += amount
        vat += line_vat
        rows.append(
            DocumentLine(
                document=doc,
                position=pos,
                product=it.product,
                description=it.description,
                qty=it.qty,
                unit_price=it.unit_price,
                vat_exempt=it.vat_exempt,
                amount=amount,
                vat=line_vat,
                restock=it.restock,
            )
        )
    DocumentLine.objects.bulk_create(rows)
    doc.subtotal, doc.vat, doc.total = subtotal, vat, subtotal + vat
    doc.save(update_fields=["subtotal", "vat", "total"])
    return doc


# ---------- stock ----------


def _lock_products(ids) -> dict[int, Product]:
    return {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=sorted(set(ids)))}


def check_stock(items: list[Item]) -> None:
    need = defaultdict(int)
    for it in items:
        if it.product:
            need[it.product.pk] += it.qty
    if not need:
        return
    products = _lock_products(need)
    levels = stock_levels(list(need))
    for pid, qty in need.items():
        if qty > levels[pid]:
            raise LedgerError(f"{products[pid].name}: only {levels[pid]} left in stock. You cannot sell {qty}.")


@transaction.atomic
def add_product(user, *, opening_qty: int = 0, **fields) -> Product:
    product = Product.objects.create(**fields)
    if opening_qty:
        StockMovement.objects.create(
            product=product,
            kind=StockMovement.Kind.OPENING,
            qty=opening_qty,
            unit_cost=product.cost_price,
            created_by=user,
            note="Starting stock",
        )
    audit(user, "create", "product", product.pk, f"Added product {product.name} with {opening_qty} in stock")
    return product


@transaction.atomic
def receive_stock(user, product, qty: int, unit_cost: int | None = None, note: str = "") -> StockMovement:
    _lock_products([product.pk])
    m = StockMovement.objects.create(
        product=product,
        kind=StockMovement.Kind.RECEIVE,
        qty=qty,
        unit_cost=unit_cost,
        note=note,
        created_by=user,
    )
    audit(user, "receive", "product", product.pk, f"Received {qty} x {product.name}")
    return m


@transaction.atomic
def take_out_stock(user, product, qty: int, reason: str) -> StockMovement:
    _lock_products([product.pk])
    on_hand = stock_levels([product.pk])[product.pk]
    try:
        money.check_take_out(on_hand, qty)
    except ValueError as e:
        raise LedgerError(str(e)) from e
    m = StockMovement.objects.create(
        product=product,
        kind=StockMovement.Kind.TAKE_OUT,
        qty=-qty,
        note=reason,
        created_by=user,
    )
    audit(user, "take_out", "product", product.pk, f"Took out {qty} x {product.name}: {reason}")
    return m


# ---------- sales, tabs, invoices ----------


def _apply_credit(customer, invoice) -> None:
    """Credit kept from earlier overpayments pays the new invoice first."""
    balance = invoice.total
    for p in payments_with_unallocated().filter(customer=customer, free__gt=0).order_by("received_on", "id"):
        if balance <= 0:
            break
        use = min(p.free, balance)
        PaymentAllocation.objects.create(payment_id=p.pk, invoice=invoice, amount=use)
        balance -= use


def _issue_invoice(user, customer, sale_lines, *, due_on=None, is_final=False, related=None) -> Document:
    settings = BusinessSettings.load()
    terms = customer.payment_terms_days if customer.payment_terms_days is not None else settings.payment_terms_days
    items = [Item(sl.description, sl.qty, sl.unit_price, sl.vat_exempt, sl.product) for sl in sale_lines]
    invoice = _new_document(
        DocType.INVOICE,
        customer,
        items,
        user,
        due_on=due_on or today() + timedelta(days=terms),
        is_final=is_final,
        related=related,
    )
    SaleLine.objects.filter(pk__in=[sl.pk for sl in sale_lines]).update(invoice=invoice)
    _apply_credit(customer, invoice)
    audit(
        user, "issue", "document", invoice.pk, f"Issued {invoice.number} to {customer.name} for KES {invoice.total:,}"
    )
    return invoice


def _exposure(customer) -> int:
    return customer_balance(customer)["balance"]


def _check_credit_limit(customer, before: int) -> Alert | None:
    if customer.credit_limit is None:
        return None
    after = _exposure(customer)
    if before <= customer.credit_limit < after:
        alert = Alert.objects.create(
            kind="credit_limit",
            customer=customer,
            message=f"{customer.name} owes KES {after:,}, over their credit limit of KES {customer.credit_limit:,}.",
        )
        from .emails import send_alert

        transaction.on_commit(lambda: send_alert(alert.pk))
        return alert
    return None


@dataclass
class SaleResult:
    invoice: Document | None
    tab: Tab | None
    payment: Payment | None
    overpaid: int
    alert: Alert | None


@transaction.atomic
def record_sale(
    user, customer, items: list[Item], *, payment: dict | None = None, due_on=None, force_invoice=False, related=None
) -> SaleResult:
    """payment: {amount, method, reference, overpay: 'refund'|'credit'} for money paid now."""
    if not items:
        raise LedgerError("Add at least one item.")
    customer = _lock_customer(customer)
    before = _exposure(customer)
    check_stock(items)
    lines = []
    for it in items:
        sl = SaleLine.objects.create(
            customer=customer,
            product=it.product,
            description=it.description,
            qty=it.qty,
            unit_price=it.unit_price,
            vat_exempt=it.vat_exempt,
            unit_cost=it.product.cost_price if it.product else None,
            created_by=user,
        )
        if it.product:
            StockMovement.objects.create(
                product=it.product,
                kind=StockMovement.Kind.SALE,
                qty=-it.qty,
                unit_cost=it.product.cost_price,
                sale_line=sl,
                created_by=user,
            )
        lines.append(sl)

    to_tab = customer.billing == Customer.Billing.TAB and not payment and not force_invoice and not customer.is_walk_in
    if to_tab:
        tab = Tab.objects.filter(customer=customer, closed_at__isnull=True).first() or Tab.objects.create(
            customer=customer
        )
        SaleLine.objects.filter(pk__in=[sl.pk for sl in lines]).update(tab=tab)
        audit(user, "tab_add", "customer", customer.pk, f"Added {len(lines)} item(s) to {customer.name}'s tab")
        return SaleResult(None, tab, None, 0, _check_credit_limit(customer, before))

    if customer.is_walk_in and not payment:
        raise LedgerError("Walk-in sales must be paid now. Pick or add the customer to sell on credit.")
    invoice = _issue_invoice(user, customer, lines, due_on=today() if payment else due_on, related=related)
    pay, over = None, 0
    if payment:
        pay, over = _record_payment(user, customer, invoice_ids=[invoice.pk], **payment)
    alert = None if payment else _check_credit_limit(customer, before)
    return SaleResult(invoice, None, pay, over, alert)


@transaction.atomic
def bill_tab(user, customer, *, close=False) -> Document | None:
    customer = _lock_customer(customer)
    tab = Tab.objects.filter(customer=customer, closed_at__isnull=True).first()
    if not tab:
        raise LedgerError(f"{customer.name} has no open tab.")
    lines = list(unbilled_lines(customer).filter(tab=tab))
    if not lines and not close:
        raise LedgerError("Nothing new to bill: every item on this tab is already on an invoice.")
    invoice = _issue_invoice(user, customer, lines, is_final=close) if lines else None
    if close:
        tab.closed_at = timezone.now()
        tab.save(update_fields=["closed_at"])
        audit(user, "close_tab", "customer", customer.pk, f"Closed {customer.name}'s tab")
    return invoice


@transaction.atomic
def remove_tab_line(user, line: SaleLine, reason: str) -> None:
    _lock_customer(line.customer)
    line = SaleLine.objects.select_for_update().get(pk=line.pk)
    if line.invoice_id or line.voided:
        raise LedgerError("This item is already on an invoice. Void the invoice or issue a credit note instead.")
    line.voided = True
    line.save(update_fields=["voided"])
    if line.product_id:
        StockMovement.objects.create(
            product_id=line.product_id,
            kind=StockMovement.Kind.VOID,
            qty=line.qty,
            sale_line=line,
            created_by=user,
            note=reason,
        )
    audit(user, "remove_tab_item", "sale_line", line.pk, f"Removed {line.qty} x {line.description} from tab: {reason}")


# ---------- payments ----------


def _record_payment(
    user, customer, *, amount, method, reference="", received_on=None, invoice_ids=None, overpay="refund"
):
    if overpay not in {"refund", "credit"}:
        raise LedgerError("Choose Refund or Keep as credit for the extra money.")
    invoices = open_invoices(customer)
    if invoice_ids:
        invoices = invoices.filter(pk__in=invoice_ids)
        if invoices.count() != len(set(invoice_ids)):
            raise LedgerError("One of the chosen invoices is already paid, void, or belongs to someone else.")
    invoices = list(invoices.select_related("customer"))
    try:
        allocations, extra = money.allocate_payment(
            amount, [(inv.pk, inv.bal, inv.partial_allowed()) for inv in invoices], customer.allow_partial
        )
    except ValueError as e:
        raise LedgerError(str(e)) from e
    payment = Payment.objects.create(
        customer=customer,
        amount=amount,
        method=method,
        reference=reference,
        received_on=received_on or today(),
        refunded=extra if overpay == "refund" else 0,
        refund_note="Overpayment refunded" if extra and overpay == "refund" else "",
        created_by=user,
    )
    PaymentAllocation.objects.bulk_create(
        [PaymentAllocation(payment=payment, invoice_id=a.invoice_id, amount=a.amount) for a in allocations]
    )
    if payment.refunded:
        Refund.objects.create(
            payment=payment,
            amount=payment.refunded,
            on=payment.received_on,
            note="Overpayment refunded",
            created_by=user,
        )
    summary = f"Recorded KES {amount:,} {payment.get_method_display()} from {customer.name}"
    if extra:
        summary += f"; KES {extra:,} extra {'to refund' if overpay == 'refund' else 'kept as credit'}"
    audit(user, "payment", "payment", payment.pk, summary)
    if customer.credit_limit is not None and _exposure(customer) <= customer.credit_limit:
        Alert.objects.filter(customer=customer, kind="credit_limit", resolved=False).update(resolved=True)
    return payment, extra


@transaction.atomic
def record_payment(user, customer, **kwargs):
    return _record_payment(user, _lock_customer(customer), **kwargs)


@transaction.atomic
def refund_credit(user, customer, amount: int, note: str) -> int:
    customer = _lock_customer(customer)
    rows = list(payments_with_unallocated().filter(customer=customer, free__gt=0).order_by("received_on", "id"))
    available = sum(p.free for p in rows)
    if amount > available:
        raise LedgerError(f"{customer.name} only has KES {available:,} in credit.")
    left = amount
    for p in rows:
        if left == 0:
            break
        use = min(p.free, left)
        Payment.objects.filter(pk=p.pk).update(refunded=F("refunded") + use, refund_note=note[:200])
        Refund.objects.create(payment_id=p.pk, amount=use, on=today(), note=note[:200], created_by=user)
        left -= use
    audit(user, "refund", "customer", customer.pk, f"Refunded KES {amount:,} credit to {customer.name}: {note}")
    return amount


@transaction.atomic
def void_payment(user, payment, reason: str) -> None:
    _lock_customer(payment.customer)
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.void:
        raise LedgerError("This payment is already void.")
    if payment.refunded:
        raise LedgerError("Part of this payment was refunded. Record the correction as a credit note instead.")
    if payment.method == Payment.Method.CREDIT_NOTE:
        raise LedgerError("Void the credit note instead; this money came from it.")
    payment.allocations.all().delete()
    payment.void, payment.void_reason = True, reason
    payment.save(update_fields=["void", "void_reason"])
    now = timezone.now()
    Document.objects.filter(payment=payment, void=False).update(
        void=True,
        void_reason=f"Payment voided: {reason}"[:200],
        voided_at=now,
        voided_by=user,
    )
    audit(user, "void", "payment", payment.pk, f"Voided payment of KES {payment.amount:,}: {reason}")


@transaction.atomic
def make_receipt(user, payment) -> Document:
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    existing = Document.objects.filter(payment=payment, void=False).first()
    if existing:
        return existing
    if payment.void:
        raise LedgerError("This payment is void.")
    items = [
        Item(f"Payment for invoice {a.invoice.number}", 1, a.amount, vat_exempt=True)
        for a in payment.allocations.select_related("invoice").order_by("id")
    ]
    if payment.unallocated() > 0:
        items.append(Item("Kept as credit for the next invoice", 1, payment.unallocated(), vat_exempt=True))
    if not items:
        raise LedgerError("Nothing to put on a receipt: the whole payment was refunded.")
    receipt = _new_document(
        DocType.RECEIPT, payment.customer, items, user, payment=payment, issued_on=payment.received_on
    )
    audit(user, "issue", "document", receipt.pk, f"Issued receipt {receipt.number}")
    return receipt


# ---------- quotations ----------


@transaction.atomic
def create_quotation(user, customer, items: list[Item], *, valid_until=None, lead=None) -> Document:
    settings = BusinessSettings.load()
    qtn = _new_document(
        DocType.QUOTATION,
        customer,
        items,
        user,
        due_on=valid_until or today() + timedelta(days=settings.quotation_valid_days),
        lead=lead,
    )
    if lead is not None:
        lead.status = "quoted"
        lead.save(update_fields=["status", "updated_at"])
    audit(user, "issue", "document", qtn.pk, f"Issued quotation {qtn.number} to {customer.name}")
    return qtn


@transaction.atomic
def convert_quotation(user, qtn) -> SaleResult:
    qtn = Document.objects.select_for_update().get(pk=qtn.pk)
    if qtn.doc_type != DocType.QUOTATION or qtn.void:
        raise LedgerError("Only a live quotation can become an invoice.")
    if qtn.children.filter(doc_type=DocType.INVOICE, void=False).exists():
        raise LedgerError("This quotation already has an invoice.")
    items = [Item(ln.description, ln.qty, ln.unit_price, ln.vat_exempt, ln.product) for ln in qtn.lines.all()]
    return record_sale(user, qtn.customer, items, force_invoice=True, related=qtn)


# ---------- corrections ----------


def _can_void(user) -> None:
    profile = user.ledger_profile
    if not profile.is_owner and not BusinessSettings.load().staff_can_void:
        raise LedgerError("Only the owner can void. Ask the owner, or ask them to allow staff to void.")


@transaction.atomic
def void_document(user, doc, reason: str) -> None:
    _can_void(user)
    _lock_customer(doc.customer)
    doc = Document.objects.select_for_update().get(pk=doc.pk)
    if doc.void:
        raise LedgerError(f"{doc.number} is already void.")
    if doc.doc_type == DocType.INVOICE:
        if doc.children.filter(doc_type=DocType.CREDIT_NOTE, void=False).exists():
            raise LedgerError("This invoice has credit notes. Void them first.")
        paid = doc.paid_amount()
        doc.allocations.all().delete()  # money paid stays with the customer as credit
        for sl in doc.sale_lines.filter(voided=False):
            sl.voided = True
            sl.save(update_fields=["voided"])
            if sl.product_id:
                StockMovement.objects.create(
                    product_id=sl.product_id,
                    kind=StockMovement.Kind.VOID,
                    qty=sl.qty,
                    sale_line=sl,
                    created_by=user,
                    note=f"{doc.number} voided",
                )
        extra = f"; KES {paid:,} already paid is now credit" if paid else ""
    elif doc.doc_type == DocType.CREDIT_NOTE:
        cn_pay = Payment.objects.filter(source_document=doc, void=False).first()
        if cn_pay and (cn_pay.refunded or cn_pay.allocated()):
            raise LedgerError("The money from this credit note was already refunded or used. It cannot be voided.")
        if cn_pay:
            cn_pay.void, cn_pay.void_reason = True, "Credit note voided"
            cn_pay.save(update_fields=["void", "void_reason"])
        restock = [ln for ln in doc.lines.all() if ln.restock and ln.product_id]
        check_stock([Item(ln.description, ln.qty, 0, product=ln.product) for ln in restock])
        for ln in restock:
            StockMovement.objects.create(
                product_id=ln.product_id,
                kind=StockMovement.Kind.TAKE_OUT,
                qty=-ln.qty,
                created_by=user,
                note=f"{doc.number} voided",
            )
        extra = ""
    elif doc.doc_type == DocType.RECEIPT:
        extra = " (the payment itself is unchanged)"
    else:
        extra = ""
    doc.void, doc.void_reason, doc.voided_at, doc.voided_by = True, reason, timezone.now(), user
    doc.save(update_fields=["void", "void_reason", "voided_at", "voided_by"])
    audit(user, "void", "document", doc.pk, f"Voided {doc.number}: {reason}{extra}")


@transaction.atomic
def credit_note(user, invoice, items: list[Item], reason: str, *, overpay="refund") -> Document:
    if overpay not in {"refund", "credit"}:
        raise LedgerError("Choose Refund or Keep as credit.")
    _lock_customer(invoice.customer)
    invoice = invoices_with_balance().get(pk=invoice.pk)
    if invoice.void:
        raise LedgerError("This invoice is void.")
    if not items:
        raise LedgerError("Add at least one line to the credit note.")
    prior = invoice.children.filter(doc_type=DocType.CREDIT_NOTE, void=False)
    prior_total = prior.aggregate(t=Coalesce(Sum("total"), 0))["t"]
    percent = invoice.vat_percent
    total = money.document_totals([money.Line(i.qty, i.unit_price, i.vat_exempt) for i in items], percent).total
    if total > invoice.total - prior_total:
        raise LedgerError(
            f"A credit note cannot be more than what is left on the invoice: KES {invoice.total - prior_total:,}."
        )
    # Restocked quantity cannot exceed what this invoice sold, counting earlier credit notes.
    sold = defaultdict(int)
    for ln in invoice.lines.filter(product__isnull=False):
        sold[ln.product_id] += ln.qty
    for ln in DocumentLine.objects.filter(document__in=prior, restock=True, product__isnull=False):
        sold[ln.product_id] -= ln.qty
    for it in items:
        if it.restock:
            if not it.product or it.qty > sold.get(it.product.pk, 0):
                raise LedgerError(f"{it.description}: you can only return items this invoice sold.")
            sold[it.product.pk] -= it.qty
    applied = min(total, max(invoice.bal, 0))
    cn = _new_document(
        DocType.CREDIT_NOTE, invoice.customer, items, user, related=invoice, notes=reason[:300], percent=percent
    )
    cn.credit_applied = applied
    cn.save(update_fields=["credit_applied"])
    for it in items:
        if it.restock:
            StockMovement.objects.create(
                product=it.product,
                kind=StockMovement.Kind.RETURN,
                qty=it.qty,
                created_by=user,
                note=f"Returned on {cn.number}",
            )
    extra = total - applied
    if extra:
        cn_pay = Payment.objects.create(
            customer=invoice.customer,
            amount=extra,
            method=Payment.Method.CREDIT_NOTE,
            reference=cn.number,
            received_on=today(),
            refunded=extra if overpay == "refund" else 0,
            refund_note="Credit note refunded" if overpay == "refund" else "",
            source_document=cn,
            created_by=user,
        )
        if overpay == "refund":
            Refund.objects.create(
                payment=cn_pay, amount=extra, on=today(), note="Credit note refunded", created_by=user
            )
    audit(user, "issue", "document", cn.pk, f"Issued credit note {cn.number} against {invoice.number}: {reason}")
    return cn
