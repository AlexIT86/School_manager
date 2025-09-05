# apps/grades/apps.py
from django.apps import AppConfig


class GradesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.grades'
    verbose_name = 'Note și Absențe'

    def ready(self):
        # Import signals pentru auto-calculare statistici
        import apps.grades.signals