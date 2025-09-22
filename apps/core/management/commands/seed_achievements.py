from django.core.management.base import BaseCommand


ACHIEVEMENTS = [
    # Note
    ('FIRST_10', 'Prima notă de 10', 'Obține prima ta notă de 10.', 'note', 'fas fa-star', 20),
    ('THREE_10_STREAK', 'Triplă de 10', 'Obține trei note de 10 consecutive.', 'note', 'fas fa-fire', 40),
    ('SUBJECT_AVG_9', 'Excelență la o materie', 'Menține media de minim 9 la o materie.', 'note', 'fas fa-medal', 30),
    ('TEN_NOTES_MONTH', 'Harnic în această lună', 'Primește cel puțin 10 note într-o lună.', 'note', 'fas fa-calendar-check', 25),
    ('NO_LOW_GRADES_MONTH', 'Fără note sub 7', 'O lună întreagă fără note sub 7.', 'note', 'fas fa-thumbs-up', 25),

    # Absențe
    ('NO_ABSENCES_30D', 'Prezență impecabilă', '30 de zile fără absențe.', 'absente', 'fas fa-user-check', 30),
    ('MOTIVATE_ABSENCE', 'Responsabil', 'Motivează prima ta absență.', 'absente', 'fas fa-file-signature', 10),

    # Teme
    ('FIRST_HOMEWORK_ON_TIME', 'Start bun', 'Finalizează prima temă la timp.', 'teme', 'fas fa-check-circle', 10),
    ('FIVE_HOMEWORKS_ROW', 'În ritm', 'Finalizează 5 teme la rând la timp.', 'teme', 'fas fa-tasks', 25),
    ('HOMEWORK_STREAK_14', 'Două săptămâni perfecte', '14 zile consecutive fără teme întârziate.', 'teme', 'fas fa-bolt', 40),
    ('HOMEWORK_50_DONE', 'Maratonistul temelor', 'Finalizează cel puțin 50 de teme.', 'teme', 'fas fa-running', 35),
    ('HOMEWORK_10_IMAGES', 'Galerie bogată', 'Încarcă cel puțin 10 imagini la teme.', 'teme', 'fas fa-images', 20),
    ('HOMEWORK_FIRST_SHARED', 'Colegul generos', 'Partajează prima ta temă cu clasa.', 'teme', 'fas fa-share-alt', 15),

    # Program și organizare (achievements eliminate la cerere)

    # Progres general
    ('FIRST_LOGIN_DAY', 'Bun venit!', 'Te-ai logat în prima zi.', 'general', 'fas fa-door-open', 5),
    ('SEVEN_DAYS_ACTIVE', 'Constanță', 'Activ în 7 zile diferite.', 'general', 'fas fa-history', 20),
]


class Command(BaseCommand):
    help = 'Seed achievements catalog'

    def handle(self, *args, **options):
        from apps.core.models import Achievement
        created, updated = 0, 0
        for code, name, desc, cat, icon, pts in ACHIEVEMENTS:
            obj, was_created = Achievement.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': desc,
                    'category': cat,
                    'icon': icon,
                    'points': pts,
                    'is_active': True,
                }
            )
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
        self.stdout.write(self.style.SUCCESS(f'Seeded achievements: created={created}, updated={updated}'))


