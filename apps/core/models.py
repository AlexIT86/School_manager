from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class StudentProfile(models.Model):
    """
    Profil extins pentru elev - legat de User-ul default Django
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')

    # Informatii personale
    clasa = models.CharField(max_length=10, help_text="Ex: 6A, 7B, etc.")
    # Legătură opțională la o clasă definită global (cu orar comun)
    class_room = models.ForeignKey('schedule.ClassRoom', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    scoala = models.CharField(max_length=200, blank=True)
    telefon_parinte = models.CharField(max_length=15, blank=True)
    email_parinte = models.EmailField(blank=True)
    # Poză profil
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    # Setari aplicatie
    ore_start = models.TimeField(default='08:00', help_text="Ora de început a programului școlar")
    durata_ora = models.IntegerField(default=50, help_text="Durata unei ore în minute")
    durata_pauza = models.IntegerField(default=10, help_text="Durata pauzei în minute")
    nr_ore_pe_zi = models.IntegerField(default=7, help_text="Numărul maxim de ore pe zi")

    # Reminder settings
    reminder_teme = models.BooleanField(default=True, help_text="Notificări pentru teme")
    reminder_note = models.BooleanField(default=True, help_text="Notificări pentru note noi")
    zile_reminder_teme = models.IntegerField(default=1, help_text="Cu câte zile înainte să anunțe temele")

    # Aprobare înregistrare (de către superadmin)
    approved = models.BooleanField(default=False, help_text="Contul a fost aprobat de un administrator")
    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_students',
        help_text="Administratorul care a aprobat contul"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Student"
        verbose_name_plural = "Profile Studenți"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - Clasa {self.clasa}"

    @property
    def nume_complet(self):
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.username


class Notification(models.Model):
    """
    Sistem de notificări pentru elev
    """
    NOTIFICATION_TYPES = [
        ('tema', 'Temă de făcut'),
        ('nota', 'Notă nouă'),
        ('absenta', 'Absență nouă'),
        ('reminder', 'Reminder general'),
        ('sistem', 'Notificare sistem'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    tip = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    titlu = models.CharField(max_length=200)
    mesaj = models.TextField()

    # Link-uri opționale
    link_url = models.URLField(blank=True, help_text="Link către pagină relevantă")

    # Status
    citita = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificare"
        verbose_name_plural = "Notificări"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_tip_display()}: {self.titlu}"


# Signals pentru crearea automată a profilului
@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """Creează automat un profil student când se creează un user nou"""
    if created:
        StudentProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_student_profile(sender, instance, **kwargs):
    """Salvează profilul student când se salvează user-ul"""
    if hasattr(instance, 'student_profile'):
        instance.student_profile.save()