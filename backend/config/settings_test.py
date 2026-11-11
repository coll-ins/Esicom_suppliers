"""Settings for pytest: local SQLite, no real email."""

import os

os.environ["DJANGO_DEBUG"] = "true"
os.environ.pop("DATABASE_URL", None)

from .settings import *

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
