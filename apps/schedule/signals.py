from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import ClassScheduleEntry, ScheduleEntry, ClassRoom, apply_class_schedule_to_user
from apps.core.models import StudentProfile
from apps.subjects.models import Subject


@receiver(post_save, sender=ClassScheduleEntry)
def propagate_class_schedule_entry_to_users(sender, instance: ClassScheduleEntry, created, **kwargs):
    """Replica automat intrarea de orar a clasei la toți utilizatorii din acea clasă.
    Creează/actualizează intrarea per utilizator folosind cheia (user, zi_saptamana, numar_ora).
    """
    try:
        profiles = instance.class_room.students.select_related('user').all()
    except Exception:
        profiles = []

    for profile in profiles:
        # Mapare/creare materie pentru utilizator după nume și culoare din clasa globală
        subject, _ = Subject.objects.get_or_create(
            user=profile.user,
            nume=instance.subject_name,
            defaults={'culoare': instance.subject_color, 'activa': True}
        )

        # Upsert intrarea din orar pentru utilizator la acea zi și oră
        ScheduleEntry.objects.update_or_create(
            user=profile.user,
            zi_saptamana=instance.zi_saptamana,
            numar_ora=instance.numar_ora,
            defaults={
                'subject': subject,
                'ora_inceput': instance.ora_inceput,
                'ora_sfarsit': instance.ora_sfarsit,
                'sala': instance.sala,
                'note': instance.note,
                'tip_ora': instance.tip_ora,
            }
        )


@receiver(post_delete, sender=ClassScheduleEntry)
def remove_class_schedule_entry_from_users(sender, instance: ClassScheduleEntry, **kwargs):
    """Șterge din orarul utilizatorilor intrarea corespunzătoare când se șterge din orarul clasei."""
    users = User.objects.filter(student_profile__class_room=instance.class_room)
    ScheduleEntry.objects.filter(
        user__in=users,
        zi_saptamana=instance.zi_saptamana,
        numar_ora=instance.numar_ora,
    ).delete()


@receiver(pre_save, sender=StudentProfile)
def _track_old_class_room(sender, instance: StudentProfile, **kwargs):
    """Reține class_room vechi pentru a detecta schimbarea în post_save."""
    if instance.pk:
        try:
            old = StudentProfile.objects.get(pk=instance.pk)
            instance._old_class_room_id = old.class_room_id
        except StudentProfile.DoesNotExist:
            instance._old_class_room_id = None


@receiver(post_save, sender=StudentProfile)
def handle_student_class_room_change(sender, instance: StudentProfile, created, **kwargs):
    """Când elevul primește/își schimbă clasa:
    - La creare: dacă are clasă setată, copiază orarul clasei dacă nu există deja intrări.
    - La schimbare: șterge orarul curent și aplică orarul noii clase.
    """
    if created:
        if instance.class_room_id:
            try:
                apply_class_schedule_to_user(instance.class_room, instance.user)
            except Exception:
                pass
        return

    old_class_room_id = getattr(instance, '_old_class_room_id', None)
    if old_class_room_id != instance.class_room_id:
        # Curăță orarul existent
        ScheduleEntry.objects.filter(user=instance.user).delete()
        # Aplică orarul noii clase, dacă e setată
        if instance.class_room_id:
            try:
                apply_class_schedule_to_user(instance.class_room, instance.user)
            except Exception:
                pass
