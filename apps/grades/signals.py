"""Signals pentru aplicația grades.

Momentan acest fișier este un placeholder pentru a preveni eroarea de import
din AppConfig.ready(). Putem adăuga ulterior logica de recalcul statistic.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Grade


@receiver(post_save, sender=Grade)
def grade_saved_update_stats(sender, instance: Grade, **kwargs):
    # Loc pentru recalcularea statisticilor la salvare, dacă dorim ulterior
    return


@receiver(post_delete, sender=Grade)
def grade_deleted_update_stats(sender, instance: Grade, **kwargs):
    # Loc pentru recalcularea statisticilor la ștergere, dacă dorim ulterior
    return


