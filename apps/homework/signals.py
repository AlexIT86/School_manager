from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import date, timedelta

from .models import Homework
from .models import HomeworkFile


def _unlock(user, code, progress=0, message=None):
    from apps.core.models import Achievement, UserAchievement, Notification
    try:
        a = Achievement.objects.get(code=code, is_active=True)
    except Achievement.DoesNotExist:
        return
    ua, _ = UserAchievement.objects.get_or_create(user=user, achievement=a)
    newly = False
    if not ua.unlocked_at:
        ua.unlocked_at = timezone.now()
        newly = True
    ua.progress = max(ua.progress, progress)
    ua.save()
    if newly:
        try:
            Notification.objects.create(user=user, tip='sistem', titlu='Ai deblocat un achievement!', mesaj=f'{a.name}')
        except Exception:
            pass


@receiver(pre_save, sender=Homework)
def _track_old_fields(sender, instance: Homework, **kwargs):
    if instance.pk:
        try:
            old = Homework.objects.get(pk=instance.pk)
            instance._old_finalizata = old.finalizata
        except Homework.DoesNotExist:
            instance._old_finalizata = False


@receiver(post_save, sender=Homework)
def homework_saved_evaluate(sender, instance: Homework, created, **kwargs):
    user = instance.user

    # Prima temă finalizată la timp
    if instance.finalizata:
        was_finalized_before = getattr(instance, '_old_finalizata', False)
        on_time = bool(instance.data_finalizare and instance.data_finalizare.date() <= instance.deadline)
        if on_time and (created or not was_finalized_before):
            count_on_time = Homework.objects.filter(user=user, finalizata=True, data_finalizare__date__lte=timezone.now().date()).filter(data_finalizare__date__lte=models.F('deadline')).count() if False else None
            _unlock(user, 'FIRST_HOMEWORK_ON_TIME')

        # 5 teme la rând la timp
        recent = list(
            Homework.objects.filter(user=user, finalizata=True).order_by('-data_finalizare').values('deadline', 'data_finalizare')[:5]
        )
        if len(recent) == 5:
            ok = True
            for hw in recent:
                df = hw['data_finalizare']
                if not df or df.date() > hw['deadline']:
                    ok = False
                    break
            if ok:
                _unlock(user, 'FIVE_HOMEWORKS_ROW')

    # 14 zile consecutive fără teme întârziate (deadline în interval și finalizate la timp)
    today = date.today()
    start = today - timedelta(days=13)
    window = Homework.objects.filter(user=user, deadline__range=[start, today])
    ok = True
    for hw in window:
        if hw.deadline <= today:
            if not hw.finalizata or not hw.data_finalizare or hw.data_finalizare.date() > hw.deadline:
                ok = False
                break
    if ok and window.exists():
        _unlock(user, 'HOMEWORK_STREAK_14')

    # 50 teme finalizate total
    total_done = Homework.objects.filter(user=user, finalizata=True).count()
    if total_done >= 50:
        _unlock(user, 'HOMEWORK_50_DONE', progress=total_done)

    # Teme share-uite (primul share)
    if instance.share_with_class:
        shared_count = Homework.objects.filter(user=user, share_with_class=True).count()
        if shared_count >= 1:
            _unlock(user, 'HOMEWORK_FIRST_SHARED', progress=shared_count)


@receiver(post_save, sender=HomeworkFile)
def homework_file_saved(sender, instance: HomeworkFile, created, **kwargs):
    if not created:
        return
    user = instance.homework.user
    # 10 imagini la teme (numai tip imagine)
    total_images = HomeworkFile.objects.filter(homework__user=user, tip='imagine').count()
    if total_images >= 10:
        _unlock(user, 'HOMEWORK_10_IMAGES', progress=total_images)


