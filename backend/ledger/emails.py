"""Outgoing email. The backend is set by DJANGO_EMAIL_BACKEND (Gmail SMTP in production)."""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)

SIGN_OFF = (
    "\n\nEsicom Suppliers\nChaka Place Building, Argwings Kodhek Road, Nairobi\n"
    "0728 942 669 · esicomsuppliers@gmail.com"
)


def _send(subject: str, body: str, to: list[str], attachments=()) -> bool:
    to = [t for t in to if t]
    if not to:
        return False
    msg = EmailMessage(
        subject, body + SIGN_OFF, settings.DEFAULT_FROM_EMAIL, to, reply_to=[settings.ESICOM_ENQUIRY_EMAIL]
    )
    for name, content, mime in attachments:
        msg.attach(name, content, mime)
    try:
        msg.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Email to %s failed: %s", to, subject)
        return False


def team_emails() -> list[str]:
    """Owner and active staff."""
    User = get_user_model()
    return list(
        User.objects.filter(is_active=True, ledger_profile__isnull=False)
        .exclude(email="")
        .values_list("email", flat=True)
    )


def send_alert(alert_id: int) -> bool:
    from .models import Alert

    alert = Alert.objects.filter(pk=alert_id).first()
    if not alert:
        return False
    return _send(f"Esicom alert: {alert.message[:80]}", alert.message, team_emails())


def send_document(doc, to: str, note: str = "") -> bool:
    from .pdf import document_pdf

    kind = doc.get_doc_type_display().lower()
    body = f"Dear {doc.customer.name},\n\nPlease find attached {kind} {doc.number}"
    if doc.doc_type == "INV":
        body += f" for KES {doc.total:,}, due on {doc.due_on:%d %b %Y}" if doc.due_on else f" for KES {doc.total:,}"
    body += "."
    if note:
        body += f"\n\n{note}"
    return _send(
        f"Esicom Suppliers {kind} {doc.number}",
        body,
        [to],
        [(f"{doc.number}.pdf", document_pdf(doc), "application/pdf")],
    )


REMINDER_TEXT = {
    "before_3": "is due in 3 days, on {due}",
    "due": "is due today, {due}",
    "after_7": "was due on {due} and is now 7 days overdue",
}


def send_reminder(invoice, kind: str, balance: int) -> bool:
    from .pdf import document_pdf

    due = f"{invoice.due_on:%d %b %Y}"
    body = (
        f"Dear {invoice.customer.name},\n\nThis is a reminder that invoice {invoice.number} "
        f"{REMINDER_TEXT[kind].format(due=due)}. The balance is KES {balance:,}.\n\n"
        "If you have already paid, please ignore this message or reply with your payment reference."
    )
    return _send(
        f"Reminder: invoice {invoice.number}, KES {balance:,}",
        body,
        [invoice.customer.email],
        [(f"{invoice.number}.pdf", document_pdf(invoice), "application/pdf")],
    )


def send_reset_code(user, code: str) -> bool:
    body = (
        f"Your Esicom dashboard password reset code is {code}.\n\n"
        "It works once and expires in 15 minutes. If you did not ask for it, ignore this email."
    )
    return _send("Your Esicom password reset code", body, [user.email])


def send_statement(customer, pdf: bytes, period: str) -> bool:
    body = f"Dear {customer.name},\n\nPlease find attached your statement for {period}."
    return _send("Your Esicom Suppliers statement", body, [customer.email], [("statement.pdf", pdf, "application/pdf")])


def whatsapp_text(doc) -> str:
    kind = doc.get_doc_type_display().lower()
    text = f"Hello {doc.customer.name}, here is your Esicom Suppliers {kind} {doc.number} for KES {doc.total:,}."
    if doc.doc_type == "INV" and doc.due_on:
        text += f" Due on {doc.due_on:%d %b %Y}."
    return text + " Thank you."


def whatsapp_phone(customer) -> str:
    """wa.me wants digits only: 2547XXXXXXXX."""
    return customer.phone.lstrip("+") if customer.phone else ""
