"""Daily jobs. They run automatically on the first request of each day (see middleware.py);
a free scheduled ping (.github/workflows/daily-ping.yml) makes sure that request happens.
`python manage.py run_daily_jobs` runs them by hand."""

import logging
import threading
from datetime import timedelta

from django.db import IntegrityError, transaction

from . import money
from .models import JobRun, ReminderSent

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_started_for = {"day": None}  # this process already started today's run


def send_due_reminders(today) -> dict:
    """For each unpaid invoice, send the latest reminder whose date has come.

    Earlier reminders that were missed (server asleep) are marked skipped, never sent late:
    a "due in 3 days" email after the due date would be wrong.
    """
    from .emails import send_reminder
    from .services import invoices_with_balance

    order = ["before_3", "due", "after_7"]
    sent = skipped = 0
    invoices = (
        invoices_with_balance()
        .filter(void=False, bal__gt=0, due_on__isnull=False, due_on__gte=today - timedelta(days=7))
        .select_related("customer")
    )
    for inv in invoices:
        dates = money.reminder_dates(inv.due_on)
        done = set(inv.reminders.values_list("kind", flat=True))
        reached = [k for k in order if dates[k] <= today and k not in done]
        if not reached:
            continue
        latest = reached[-1]
        for k in reached[:-1]:
            ReminderSent.objects.get_or_create(invoice=inv, kind=k, defaults={"skipped": True})
            skipped += 1
        # Only a reminder for its own day is sent; anything older is recorded as skipped.
        if dates[latest] != today or not inv.customer.email:
            ReminderSent.objects.get_or_create(invoice=inv, kind=latest, defaults={"skipped": True})
            skipped += 1
            continue
        try:
            with transaction.atomic():
                ReminderSent.objects.create(invoice=inv, kind=latest)
        except IntegrityError:
            continue  # another worker sent it
        if send_reminder(inv, latest, inv.bal):
            sent += 1
        else:
            ReminderSent.objects.filter(invoice=inv, kind=latest).update(skipped=True)
    return {"sent": sent, "skipped": skipped}


def run_daily_jobs(today, *, force=False) -> dict | None:
    """Runs once per day. Returns None if today's run already happened."""
    if not force:
        try:
            with transaction.atomic():
                JobRun.objects.create(name="daily", day=today)
        except IntegrityError:
            return None
    result = send_due_reminders(today)
    logger.info("Daily jobs for %s: %s", today, result)
    return result


def run_daily_jobs_in_background(today) -> None:
    if _started_for["day"] == today:
        return
    if JobRun.objects.filter(name="daily", day=today).exists():
        _started_for["day"] = today
        return
    if not _lock.acquire(blocking=False):
        return
    _started_for["day"] = today

    def work():
        try:
            run_daily_jobs(today)
        except Exception:
            logger.exception("Daily jobs failed")
        finally:
            from django.db import connection

            connection.close()
            _lock.release()

    threading.Thread(target=work, daemon=True).start()
