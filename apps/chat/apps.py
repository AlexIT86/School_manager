from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chat'
    verbose_name = 'Chat intern'

    def ready(self):
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass


