from django.apps import AppConfig

from analytics.services import purge_all_caches


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "analytics"

    def ready(self):
        # This will import the signals when the app is ready
        import analytics.signals  # noqa: F401

        purge_all_caches()  # noqa: F401
