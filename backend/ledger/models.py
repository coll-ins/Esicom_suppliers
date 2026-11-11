"""Ledger data. Money is whole Kenyan shillings stored as integers.

Stock on hand is never stored: it is the sum of StockMovement rows.
Issued documents are never edited: corrections are a void or a credit note.
"""

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce, Lower

USER = settings.AUTH_USER_MODEL


class Role(models.TextChoices):
    OWNER = "owner", "Owner"
    STAFF = "staff", "Staff"


class Profile(models.Model):
    user = models.OneToOneField(USER, on_delete=models.CASCADE, related_name="ledger_profile")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    # Bumped by "Log out everywhere"; sessions carrying an older number are rejected.
    session_version = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user} ({self.role})"

    @property
    def is_owner(self):
        return self.role == Role.OWNER


class LoginAttempt(models.Model):
    """Failed logins per email address (exists or not, so attackers learn nothing)."""

    email = models.CharField(max_length=254, unique=True)
    failures = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)


class PasswordResetCode(models.Model):
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="reset_codes")
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class BusinessSettings(models.Model):
    """One row (pk=1). Blank text fields are never printed on documents."""

    kra_pin = models.CharField(max_length=20, blank=True)
    mpesa_paybill = models.CharField(max_length=10, blank=True)
    mpesa_account = models.CharField(max_length=40, blank=True)
    mpesa_till = models.CharField(max_length=10, blank=True)
    bank_name = models.CharField(max_length=80, blank=True)
    bank_branch = models.CharField(max_length=80, blank=True)
    bank_account_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(max_length=40, blank=True)
    vat_percent = models.PositiveSmallIntegerField(default=16)
    payment_terms_days = models.PositiveSmallIntegerField(default=30)
    quotation_valid_days = models.PositiveSmallIntegerField(default=14)
    staff_can_void = models.BooleanField(default=False)
    staff_can_set_vat_exempt = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Customer(models.Model):
    class Billing(models.TextChoices):
        PER_SALE = "per_sale", "One invoice per sale"
        TAB = "tab", "Running tab"

    name = models.CharField(max_length=160)
    phone = models.CharField(max_length=13, blank=True)  # stored as +2547XXXXXXXX
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=200, blank=True)
    kra_pin = models.CharField(max_length=20, blank=True)
    billing = models.CharField(max_length=10, choices=Billing.choices, default=Billing.PER_SALE)
    allow_partial = models.BooleanField(default=False)
    credit_limit = models.PositiveIntegerField(null=True, blank=True)
    payment_terms_days = models.PositiveSmallIntegerField(null=True, blank=True)
    is_walk_in = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [Lower("name")]
        constraints = [
            models.UniqueConstraint(fields=["is_walk_in"], condition=Q(is_walk_in=True), name="one_walk_in_customer"),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=160)
    unit = models.CharField(max_length=30, default="piece")
    price = models.PositiveIntegerField()  # selling price excluding VAT
    cost_price = models.PositiveIntegerField(null=True, blank=True)  # owner only
    vat_exempt = models.BooleanField(default=False)
    reorder_level = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [Lower("name")]
        constraints = [models.UniqueConstraint(Lower("name"), name="unique_product_name")]

    def __str__(self):
        return self.name

    def on_hand(self) -> int:
        return self.movements.aggregate(t=Coalesce(Sum("qty"), 0))["t"]


class StockMovement(models.Model):
    class Kind(models.TextChoices):
        OPENING = "opening", "Starting stock"
        RECEIVE = "receive", "Received"
        RETURN = "return", "Returned by customer"
        SALE = "sale", "Sold"
        TAKE_OUT = "take_out", "Taken out"
        VOID = "void", "Sale voided"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    qty = models.IntegerField()  # positive in, negative out
    unit_cost = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)
    sale_line = models.ForeignKey("SaleLine", null=True, blank=True, on_delete=models.PROTECT, related_name="movements")
    created_by = models.ForeignKey(USER, null=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Tab(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="tabs")
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["customer"], condition=Q(closed_at__isnull=True), name="one_open_tab"),
        ]


class SaleLine(models.Model):
    """One item sold. It waits on a tab until an invoice bills it."""

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="sale_lines")
    tab = models.ForeignKey(Tab, null=True, blank=True, on_delete=models.PROTECT, related_name="lines")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    description = models.CharField(max_length=200)
    qty = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()
    vat_exempt = models.BooleanField(default=False)
    unit_cost = models.PositiveIntegerField(null=True, blank=True)  # cost at time of sale, for profit
    invoice = models.ForeignKey("Document", null=True, blank=True, on_delete=models.PROTECT, related_name="sale_lines")
    voided = models.BooleanField(default=False)
    created_by = models.ForeignKey(USER, null=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class DocType(models.TextChoices):
    INVOICE = "INV", "Invoice"
    RECEIPT = "RCP", "Receipt"
    QUOTATION = "QTN", "Quotation"
    CREDIT_NOTE = "CN", "Credit note"


class Sequence(models.Model):
    doc_type = models.CharField(max_length=3, choices=DocType.choices)
    year = models.PositiveSmallIntegerField()
    last = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["doc_type", "year"], name="one_sequence_per_type_year")]


class Document(models.Model):
    doc_type = models.CharField(max_length=3, choices=DocType.choices)
    number = models.CharField(max_length=30, unique=True)
    year = models.PositiveSmallIntegerField()
    seq = models.PositiveIntegerField()
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="documents")
    issued_on = models.DateField()
    due_on = models.DateField(null=True, blank=True)  # invoice due date / quotation valid until
    subtotal = models.PositiveIntegerField(default=0)
    vat = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    vat_percent = models.PositiveSmallIntegerField(default=16)  # rate used when issued
    # Credit notes: the part of the total that reduced the invoice balance.
    credit_applied = models.PositiveIntegerField(default=0)
    allow_partial = models.BooleanField(null=True, blank=True)  # None = follow the customer
    related = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    payment = models.ForeignKey("Payment", null=True, blank=True, on_delete=models.PROTECT, related_name="receipts")
    lead = models.ForeignKey("quotes.QuoteRequest", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    is_final = models.BooleanField(default=False)  # final invoice when a tab was closed
    etims_number = models.CharField(max_length=40, blank=True)
    notes = models.CharField(max_length=300, blank=True)
    void = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=200, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(USER, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    created_by = models.ForeignKey(USER, null=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_on", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["doc_type", "year", "seq"], name="unique_document_seq"),
        ]

    def __str__(self):
        return self.number

    def paid_amount(self) -> int:
        return self.allocations.aggregate(t=Coalesce(Sum("amount"), 0))["t"]

    def credited_amount(self) -> int:
        return self.children.filter(doc_type=DocType.CREDIT_NOTE, void=False).aggregate(
            t=Coalesce(Sum("credit_applied"), 0)
        )["t"]

    def balance(self) -> int:
        if self.doc_type != DocType.INVOICE or self.void:
            return 0
        return self.total - self.paid_amount() - self.credited_amount()

    def partial_allowed(self) -> bool:
        return self.customer.allow_partial if self.allow_partial is None else self.allow_partial


class DocumentLine(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="lines")
    position = models.PositiveSmallIntegerField()
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    description = models.CharField(max_length=200)
    qty = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()
    vat_exempt = models.BooleanField(default=False)
    amount = models.PositiveIntegerField()  # qty x unit price, excluding VAT
    vat = models.PositiveIntegerField()
    restock = models.BooleanField(default=False)  # credit notes: item came back into stock

    class Meta:
        ordering = ["position"]


class Payment(models.Model):
    class Method(models.TextChoices):
        MPESA = "mpesa", "M-Pesa"
        CASH = "cash", "Cash"
        BANK = "bank", "Bank"
        CREDIT_NOTE = "credit_note", "Credit note"  # money owed back after a credit note

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="payments")
    amount = models.PositiveIntegerField()
    method = models.CharField(max_length=12, choices=Method.choices)
    reference = models.CharField(max_length=60, blank=True)
    received_on = models.DateField()
    refunded = models.PositiveIntegerField(default=0)
    refund_note = models.CharField(max_length=200, blank=True)
    source_document = models.ForeignKey(Document, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    void = models.BooleanField(default=False)
    void_reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(USER, null=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_on", "-id"]

    def allocated(self) -> int:
        return self.allocations.aggregate(t=Coalesce(Sum("amount"), 0))["t"]

    def unallocated(self) -> int:
        """Money kept as credit for the next invoice."""
        if self.void:
            return 0
        return self.amount - self.refunded - self.allocated()


class Refund(models.Model):
    """Money given back. Payment.refunded is the running sum of these for its payment."""

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    amount = models.PositiveIntegerField()
    on = models.DateField()
    note = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(USER, null=True, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-on", "-id"]


class PaymentAllocation(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="allocations")
    invoice = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="allocations")
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    user = models.ForeignKey(USER, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=40)
    entity = models.CharField(max_length=40)
    entity_id = models.CharField(max_length=40, blank=True)
    summary = models.CharField(max_length=300)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-at", "-id"]


class Alert(models.Model):
    kind = models.CharField(max_length=30)
    message = models.CharField(max_length=300)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE, related_name="+")
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class ReminderSent(models.Model):
    class Kind(models.TextChoices):
        BEFORE_3 = "before_3", "3 days before due"
        DUE = "due", "On the due date"
        AFTER_7 = "after_7", "7 days overdue"

    invoice = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="reminders")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    skipped = models.BooleanField(default=False)  # passed while the server was asleep; not sent late
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["invoice", "kind"], name="one_reminder_per_kind")]


class JobRun(models.Model):
    """Marks a daily job as done for a date, so it runs once per day."""

    name = models.CharField(max_length=40)
    day = models.DateField()
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name", "day"], name="one_job_run_per_day")]


class RequestKey(models.Model):
    """One-time key sent with a sale or payment, so a retried request never saves twice."""

    key = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name="+")
    response = models.JSONField(default=dict, encoder=DjangoJSONEncoder)
    created_at = models.DateTimeField(auto_now_add=True)
