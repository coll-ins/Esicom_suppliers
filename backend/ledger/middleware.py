import logging

from django.conf import settings

from .jobs import run_daily_jobs_in_background
from .services import today


class DailyJobsMiddleware:
    """Starts the day's jobs (reminder emails) on the first request of each day, after the response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(settings, "LEDGER_RUN_DAILY_JOBS", True) and request.path.startswith("/api/"):
            try:
                run_daily_jobs_in_background(today())
            except Exception:  # noqa: BLE001  never break a request because of the job check
                logging.getLogger(__name__).exception("Could not start daily jobs")
        return response
