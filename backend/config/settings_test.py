"""Settings for pytest: local SQLite, no real email."""

import os

os.environ["DJANGO_DEBUG"] = "true"
os.environ.pop("DATABASE_URL", None)
for _key in ("NEON_DATABASE_URL", "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"):
    os.environ.pop(_key, None)

from .settings import *  # noqa: F403

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
LEDGER_RUN_DAILY_JOBS = False

# A second database so the move_database command can be tested.
DATABASES["neon"] = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:", "TEST": {"NAME": ":memory:"}}
