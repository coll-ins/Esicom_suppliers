from django.core.management.base import BaseCommand

from ledger.jobs import run_daily_jobs
from ledger.services import today


class Command(BaseCommand):
    help = "Send today's due-date reminder emails (normally runs by itself on the first request of the day)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Run even if today's run already happened.")

    def handle(self, *args, force=False, **options):
        result = run_daily_jobs(today(), force=force)
        self.stdout.write("Already ran today." if result is None else f"Done: {result}")
