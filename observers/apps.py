from django.apps import AppConfig


class ObserverConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "observers"

    def ready(self):
        # This will import the signals when the app is ready
        import observers.signals  # noqa: F401
