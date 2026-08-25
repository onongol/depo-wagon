from django.apps import AppConfig


class AiServiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_service"

    def ready(self):
        import apps.ai_service.signals  # noqa: F401
