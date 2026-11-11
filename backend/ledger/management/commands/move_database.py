"""Copy everything from the current database (DATABASE_URL) into a new one (NEON_DATABASE_URL).

Runs on every start and does nothing unless NEON_DATABASE_URL is set. It refuses to copy into a
database that already holds data, so it can never overwrite or duplicate anything. After it reports
"copied", switch DATABASE_URL to the Neon URL and remove NEON_DATABASE_URL.
"""

import tempfile
from io import StringIO

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction

SKIP = ["contenttypes", "auth.permission", "sessions"]  # recreated by migrate; sessions not needed


class Command(BaseCommand):
    help = "Copy all data into the database at NEON_DATABASE_URL (only if it is empty)."

    def handle(self, *args, **options):
        if "neon" not in settings.DATABASES:
            self.stdout.write("move_database: NEON_DATABASE_URL not set, nothing to do.")
            return
        call_command("migrate", database="neon", interactive=False, verbosity=0)
        User = apps.get_model("auth", "User")
        if User.objects.using("neon").exists():
            self.stdout.write("move_database: the new database already has data. Not copying again.")
            return
        with tempfile.NamedTemporaryFile(suffix=".json") as dump:
            call_command(
                "dumpdata",
                exclude=SKIP,
                natural_foreign=True,
                natural_primary=True,
                output=dump.name,
                database="default",
                verbosity=0,
            )
            with transaction.atomic(using="neon"):
                call_command("loaddata", dump.name, database="neon", verbosity=0)
        self._reset_sequences()
        problems = []
        for model in apps.get_models():
            label = model._meta.label
            if model._meta.app_label in {"contenttypes", "sessions"} or label == "auth.Permission":
                continue
            if not model._meta.managed or model._meta.proxy:
                continue
            old, new = model.objects.using("default").count(), model.objects.using("neon").count()
            if old != new:
                problems.append(f"{label}: {old} -> {new}")
        if problems:
            raise CommandError("move_database: row counts differ: " + "; ".join(problems))
        self.stdout.write("move_database: copied. Every table has the same number of rows.")

    def _reset_sequences(self):
        conn = connections["neon"]
        out = StringIO()
        for config in apps.get_app_configs():
            if config.models_module is None:
                continue
            call_command("sqlsequencereset", config.label, database="neon", stdout=out, no_color=True)
        sql = out.getvalue().strip()
        if sql:
            with conn.cursor() as cursor:
                cursor.execute(sql)
