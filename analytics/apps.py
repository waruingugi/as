from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "analytics"

    def ready(self):
        # This will import the signals when the app is ready
        import analytics.signals  # noqa: F401
