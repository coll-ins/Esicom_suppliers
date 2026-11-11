"""Create the owner account from LEDGER_OWNER_EMAIL if no owner exists yet.

The account starts with no password. The owner sets one with "Forgot password" on the
dashboard login page, which emails a 6-digit code. Safe to run on every deploy.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from ledger.models import Profile, Role


class Command(BaseCommand):
    help = "Create the owner account (LEDGER_OWNER_EMAIL) if there is none."

    def add_arguments(self, parser):
        parser.add_argument("--email", default=os.environ.get("LEDGER_OWNER_EMAIL", ""))
        parser.add_argument("--name", default=os.environ.get("LEDGER_OWNER_NAME", "Owner"))

    @transaction.atomic
    def handle(self, *args, email, name, **options):
        if Profile.objects.filter(role=Role.OWNER).exists():
            self.stdout.write("Owner already exists.")
            return
        email = email.strip().lower()
        if not email:
            self.stdout.write("No owner yet. Set LEDGER_OWNER_EMAIL to create one.")
            return
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            first, _, last = name.partition(" ")
            user = User(username=email, email=email, first_name=first, last_name=last)
            user.set_unusable_password()
            user.save()
        Profile.objects.create(user=user, role=Role.OWNER)
        self.stdout.write(f"Owner {email} created. Use 'Forgot password' on the dashboard to set the password.")
