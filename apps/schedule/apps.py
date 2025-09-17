# apps/schedule/apps.py
from django.apps import AppConfig

class ScheduleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.schedule'
    verbose_name = 'Orar Școlar'

    def ready(self):
        # Înregistrează semnalele pentru sincronizarea orarului
        from . import signals  # noqa: F401