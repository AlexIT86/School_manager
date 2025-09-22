"""Signals pentru aplicația grades.

Momentan acest fișier este un placeholder pentru a preveni eroarea de import
din AppConfig.ready(). Putem adăuga ulterior logica de recalcul statistic.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Grade
from django.utils import timezone
from django.db.models import Avg, Count, Q

def _unlock(user, code, progress=0):
    from apps.core.models import Achievement, UserAchievement
    try:
        a = Achievement.objects.get(code=code, is_active=True)
    except Achievement.DoesNotExist:
        return
    ua, _ = UserAchievement.objects.get_or_create(user=user, achievement=a)
    if not ua.unlocked_at:
        ua.unlocked_at = timezone.now()
    ua.progress = max(ua.progress, progress)
    ua.save()


@receiver(post_save, sender=Grade)
def grade_saved_update_stats(sender, instance: Grade, **kwargs):
    # Achievements legate de note
    user = instance.user
    if instance.tip == 'nota' and instance.valoare:
        # Prima notă de 10
        if float(instance.valoare) >= 10:
            tens = Grade.objects.filter(user=user, tip='nota', valoare__gte=10).count()
            if tens == 1:
                _unlock(user, 'FIRST_10')

        # 3 note consecutive de 10 (verificare simplă: ultimele 3 note)
        last3 = list(Grade.objects.filter(user=user, tip='nota').order_by('-data', '-created_at').values_list('valoare', flat=True)[:3])
        if len(last3) == 3 and all(float(v) >= 10 for v in last3):
            _unlock(user, 'THREE_10_STREAK')

        # Media 9+ la o materie (rapid)
        subject_avg = Grade.objects.filter(user=user, subject=instance.subject, tip='nota').aggregate(avg=Avg('valoare'))['avg'] or 0
        if float(subject_avg) >= 9:
            _unlock(user, 'SUBJECT_AVG_9')

    # Absențe: 30 zile fără absențe
    from datetime import date, timedelta
    today = date.today()
    last30 = Grade.objects.filter(user=user, tip__in=['absenta', 'absenta_motivata']).filter(data__gte=today - timedelta(days=30)).count()
    if last30 == 0:
        _unlock(user, 'NO_ABSENCES_30D')


@receiver(post_delete, sender=Grade)
def grade_deleted_update_stats(sender, instance: Grade, **kwargs):
    return


