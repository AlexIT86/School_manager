from django.core.management.base import BaseCommand


TARGET_CODES = {
    'FULL_WEEK_SCHEDULE',
    'SUBJECTS_10',
    'FILES_20',
}


class Command(BaseCommand):
    help = 'Delete specific achievements (and user links) completely from the system.'

    def handle(self, *args, **options):
        from apps.core.models import Achievement, UserAchievement
        deleted_users = 0
        deleted_ach = 0

        ach_qs = Achievement.objects.filter(code__in=TARGET_CODES)
        ach_ids = list(ach_qs.values_list('id', flat=True))
        if ach_ids:
            deleted_users, _ = UserAchievement.objects.filter(achievement_id__in=ach_ids).delete()
            deleted_ach, _ = ach_qs.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Purged achievements: {len(TARGET_CODES)} codes targeted, user_links_deleted={deleted_users}, achievements_deleted={deleted_ach}"
        ))


