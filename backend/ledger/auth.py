import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model, logout
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission

from .models import LoginAttempt, PasswordResetCode, Profile

MAX_FAILURES = 5
LOCK_MINUTES = 15
RESET_MINUTES = 15
RESET_MAX_ATTEMPTS = 5
RESET_MAX_PER_HOUR = 3
SESSION_KEY = "ledger_sv"


class LedgerSessionAuthentication(SessionAuthentication):
    """Django session + CSRF, and rejects sessions ended by "Log out everywhere"."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        profile = Profile.objects.filter(user=result[0]).first()
        if profile is None or request._request.session.get(SESSION_KEY) != profile.session_version:
            logout(request._request)
            return None
        return result


class IsLedgerUser(BasePermission):
    message = "Log in to continue."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, "ledger_profile"))


class IsOwner(BasePermission):
    message = "Only the owner can do this."

    def has_permission(self, request, view):
        return IsLedgerUser().has_permission(request, view) and request.user.ledger_profile.is_owner


def is_owner(user) -> bool:
    return bool(user and user.is_authenticated and hasattr(user, "ledger_profile") and user.ledger_profile.is_owner)


def normalize_email(email) -> str:
    return str(email or "").strip().lower()[:254]


def find_user(email: str):
    User = get_user_model()
    return User.objects.filter(email__iexact=email, is_active=True, ledger_profile__isnull=False).first()


def check_lock(email: str) -> str | None:
    attempt = LoginAttempt.objects.filter(email=email).first()
    if attempt and attempt.locked_until and attempt.locked_until > timezone.now():
        minutes = max(1, int((attempt.locked_until - timezone.now()).total_seconds() // 60) + 1)
        return f"Too many wrong passwords. This account is locked. Try again in {minutes} minute(s)."
    return None


@transaction.atomic
def record_failure(email: str) -> str:
    LoginAttempt.objects.get_or_create(email=email)
    attempt = LoginAttempt.objects.select_for_update().get(email=email)  # parallel guesses all count
    if attempt.locked_until and attempt.locked_until <= timezone.now():
        attempt.failures = 0
        attempt.locked_until = None
    attempt.failures += 1
    if attempt.failures >= MAX_FAILURES:
        attempt.locked_until = timezone.now() + timedelta(minutes=LOCK_MINUTES)
        attempt.save()
        return f"Too many wrong passwords. This account is locked for {LOCK_MINUTES} minutes."
    attempt.save()
    left = MAX_FAILURES - attempt.failures
    tries = "try" if left == 1 else "tries"
    return f"Wrong email or password. {left} more wrong {tries} locks the account for {LOCK_MINUTES} minutes."


def clear_failures(email: str) -> None:
    LoginAttempt.objects.filter(email=email).delete()


def start_session(request, user) -> None:
    from django.contrib.auth import login

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session[SESSION_KEY] = user.ledger_profile.session_version


def end_all_sessions(user) -> None:
    Profile.objects.filter(user=user).update(session_version=user.ledger_profile.session_version + 1)
    user.ledger_profile.refresh_from_db()


def _hash(code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def issue_reset_code(user) -> str | None:
    """Returns the code to email, or None if the hourly limit is reached."""
    hour_ago = timezone.now() - timedelta(hours=1)
    if PasswordResetCode.objects.filter(user=user, created_at__gte=hour_ago).count() >= RESET_MAX_PER_HOUR:
        return None
    # Earlier codes stay valid until they expire, so repeated requests cannot block a reset.
    code = f"{secrets.randbelow(1_000_000):06d}"
    PasswordResetCode.objects.create(
        user=user, code_hash=_hash(code), expires_at=timezone.now() + timedelta(minutes=RESET_MINUTES)
    )
    return code


def check_reset_code(user, code: str, *, use: bool = True) -> str | None:
    """Returns an error message, or None if the code matches a live code (marked used when use=True)."""
    live = list(
        PasswordResetCode.objects.select_for_update().filter(
            user=user, used=False, expires_at__gt=timezone.now(), attempts__lt=RESET_MAX_ATTEMPTS
        )
    )
    if not live:
        return "This code has expired or was already used. Ask for a new code."
    digest = _hash(str(code).strip())
    match = next((rc for rc in live if hmac.compare_digest(rc.code_hash, digest)), None)
    if match is None:
        PasswordResetCode.objects.filter(pk__in=[rc.pk for rc in live]).update(attempts=F("attempts") + 1)
        return "That code is wrong. Check the latest email and type the 6 digits."
    if use:
        PasswordResetCode.objects.filter(user=user, used=False).update(used=True)
    return None


class LockedAdminLoginForm(AdminAuthenticationForm):
    """Django admin login with the same 5-tries / 15-minute lock as the dashboard."""

    def clean(self):
        email = normalize_email(self.data.get("username"))
        locked = check_lock(email)
        if locked:
            raise ValidationError(locked)
        try:
            data = super().clean()
        except ValidationError:
            record_failure(email)
            raise
        clear_failures(email)
        return data
