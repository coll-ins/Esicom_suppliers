from django.apps import AppConfig


class LedgerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ledger"

    def ready(self):
        from django.contrib import admin

        from .auth import LockedAdminLoginForm

        admin.site.login_form = LockedAdminLoginForm
