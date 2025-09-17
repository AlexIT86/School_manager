from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from apps.subjects.models import Subject
import os
from apps.schedule.models import ClassRoom


def homework_file_upload_path(instance, filename):
    """Generează calea pentru fișierele uploadate la teme"""
    return f'homework/{instance.homework.id}/{filename}'


class Homework(models.Model):
    """
    Model pentru temele de casă
    """
    PRIORITY_CHOICES = [
        ('scazuta', 'Scăzută'),
        ('normala', 'Normală'),
        ('ridicata', 'Ridicată'),
        ('urgenta', 'Urgentă'),
    ]

    DIFFICULTY_CHOICES = [
        ('usoara', 'Ușoară'),
        ('medie', 'Medie'),
        ('grea', 'Grea'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='homework')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='homework_set')

    # Detalii temă
    titlu = models.CharField(max_length=200, help_text="Titlul temei")
    descriere = models.TextField(help_text="Descrierea detaliată a temei")

    # Pagini/exerciții
    pagini = models.CharField(max_length=100, blank=True, help_text="Ex: pag. 25-30, ex. 1-5")
    exercitii = models.TextField(blank=True, help_text="Detalii despre exerciții")

    # Deadline și prioritate
    data_primita = models.DateField(default=date.today, help_text="Când a fost dată tema")
    deadline = models.DateField(help_text="Până când trebuie făcută tema")
    prioritate = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normala')
    dificultate = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='medie')

    # Timp estimat și progress
    timp_estimat = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Timp estimat în minute pentru finalizare"
    )
    timp_lucrat = models.PositiveIntegerField(
        default=0,
        help_text="Timp efectiv lucrat în minute"
    )
    progres = models.PositiveIntegerField(
        default=0,
        help_text="Progres în procente (0-100)"
    )

    # Status
    finalizata = models.BooleanField(default=False)
    data_finalizare = models.DateTimeField(blank=True, null=True)

    # Sharing
    share_with_class = models.BooleanField(
        default=False,
        help_text="Dacă este activat, tema va fi vizibilă tuturor elevilor din clasa setată în profilul tău."
    )
    shared_class_room = models.ForeignKey(
        ClassRoom,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='shared_homeworks',
        help_text="Clasa cu care este partajată tema"
    )
    shared_at = models.DateTimeField(blank=True, null=True)

    # Reminder
    reminder_activ = models.BooleanField(default=True)
    zile_reminder = models.PositiveIntegerField(
        default=1,
        help_text="Cu câte zile înainte de deadline să trimită reminder"
    )

    # Note și feedback
    note_personale = models.TextField(blank=True, help_text="Notițe personale despre temă")
    dificultati = models.TextField(blank=True, help_text="Dificultăți întâmpinate")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Temă"
        verbose_name_plural = "Teme"
        ordering = ['deadline', '-prioritate']

    def __str__(self):
        return f"{self.subject.nume} - {self.titlu}"

    def save(self, *args, **kwargs):
        # Setează data finalizării când tema devine finalizată
        if self.finalizata and not self.data_finalizare:
            self.data_finalizare = timezone.now()
        elif not self.finalizata:
            self.data_finalizare = None

        # Configurează câmpurile de share
        if self.share_with_class:
            if not self.shared_class_room:
                try:
                    profile = self.user.student_profile
                    if getattr(profile, 'class_room', None):
                        self.shared_class_room = profile.class_room
                except Exception:
                    pass
            if self.shared_at is None:
                self.shared_at = timezone.now()
        else:
            # Dacă se dezactivează share, păstrează auditul (shared_at), dar scoate clasa
            self.shared_class_room = self.shared_class_room if self.shared_class_room else None

        super().save(*args, **kwargs)

    @property
    def zile_ramase(self):
        """Calculează câte zile mai sunt până la deadline"""
        if self.finalizata:
            return 0
        delta = self.deadline - date.today()
        return delta.days

    @property
    def este_intarziata(self):
        """Verifică dacă tema este întârziată"""
        return not self.finalizata and date.today() > self.deadline

    @property
    def culoare_urgenta(self):
        """Returnează culoarea bazată pe urgență"""
        if self.este_intarziata:
            return '#dc3545'  # roșu
        elif self.zile_ramase <= 1:
            return '#ffc107'  # galben
        elif self.prioritate == 'urgenta':
            return '#fd7e14'  # portocaliu
        else:
            return '#28a745'  # verde

    @property
    def status_display(self):
        """Returnează statusul pentru afișare"""
        if self.finalizata:
            return "Finalizată"
        elif self.este_intarziata:
            return "Întârziată"
        elif self.zile_ramase == 0:
            return "Azi"
        elif self.zile_ramase == 1:
            return "Mâine"
        else:
            return f"{self.zile_ramase} zile"

    @property
    def timp_ramas_estimat(self):
        """Calculează timpul rămas estimat bazat pe progres"""
        if self.timp_estimat and self.progres < 100:
            timp_ramas = self.timp_estimat * (100 - self.progres) / 100
            return int(timp_ramas)
        return 0

    def marcheaza_finalizata(self):
        """Marchează tema ca finalizată"""
        self.finalizata = True
        self.progres = 100
        self.data_finalizare = timezone.now()
        self.save()

    def adauga_timp_lucrat(self, minute):
        """Adaugă timp lucrat la temă"""
        self.timp_lucrat += minute
        self.save()


class HomeworkFile(models.Model):
    """
    Fișiere atașate la o temă (resurse, soluții, etc.)
    """
    FILE_TYPES = [
        ('resursa', 'Resursă pentru temă'),
        ('solutie', 'Soluția mea'),
        ('imagine', 'Imagine/Screenshot'),
        ('document', 'Document'),
        ('altele', 'Altele'),
    ]

    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='files')
    nume = models.CharField(max_length=200, help_text="Numele fișierului")
    fisier = models.FileField(upload_to=homework_file_upload_path)
    tip = models.CharField(max_length=20, choices=FILE_TYPES, default='altele')
    descriere = models.TextField(blank=True)

    # Metadata
    marime = models.PositiveIntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fișier Temă"
        verbose_name_plural = "Fișiere Teme"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.homework.titlu} - {self.nume}"

    def save(self, *args, **kwargs):
        if self.fisier:
            self.marime = self.fisier.size

            # Auto-detectează tipul
            _, ext = os.path.splitext(self.fisier.name.lower())
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                self.tip = 'imagine'
            elif ext in ['.pdf', '.doc', '.docx', '.txt']:
                self.tip = 'document'

        super().save(*args, **kwargs)

    @property
    def marime_formatata(self):
        """Returnează mărimea fișierului în format human-readable"""
        if not self.marime:
            return "Necunoscut"
        size = float(self.marime)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class HomeworkSession(models.Model):
    """
    Sesiuni de lucru la o temă (pentru tracking timp)
    """
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='sessions')

    # Timp
    inceput = models.DateTimeField(auto_now_add=True)
    sfarsit = models.DateTimeField(blank=True, null=True)
    durata_minute = models.PositiveIntegerField(default=0)

    # Progress în această sesiune
    progres_inainte = models.PositiveIntegerField(default=0)
    progres_dupa = models.PositiveIntegerField(default=0)

    # Note
    note_sesiune = models.TextField(blank=True, help_text="Ce s-a făcut în această sesiune")
    dificultati_sesiune = models.TextField(blank=True, help_text="Probleme întâmpinate")

    class Meta:
        verbose_name = "Sesiune Lucru Temă"
        verbose_name_plural = "Sesiuni Lucru Teme"
        ordering = ['-inceput']

    def __str__(self):
        return f"{self.homework.titlu} - Sesiune {self.inceput.strftime('%d.%m.%Y %H:%M')}"

    def finalizeaza_sesiune(self, progres_nou=None):
        """Finalizează sesiunea de lucru"""
        if not self.sfarsit:
            self.sfarsit = timezone.now()
            self.durata_minute = int((self.sfarsit - self.inceput).total_seconds() / 60)

            if progres_nou is not None:
                self.progres_dupa = progres_nou
                self.homework.progres = progres_nou

            # Adaugă timpul la temă
            self.homework.adauga_timp_lucrat(self.durata_minute)
            self.save()


class HomeworkReminder(models.Model):
    """
    Reminder-uri pentru teme
    """
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='reminders')

    # Când să trimită reminder-ul
    data_reminder = models.DateField()
    ora_reminder = models.TimeField(default='18:00')

    # Status
    trimis = models.BooleanField(default=False)
    data_trimitere = models.DateTimeField(blank=True, null=True)

    # Mesaj personalizat
    mesaj_custom = models.TextField(blank=True, help_text="Mesaj personalizat pentru reminder")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reminder Temă"
        verbose_name_plural = "Reminder-uri Teme"
        ordering = ['data_reminder', 'ora_reminder']
        unique_together = ['homework', 'data_reminder']

    def __str__(self):
        return f"Reminder: {self.homework.titlu} - {self.data_reminder}"

    @property
    def mesaj_default(self):
        """Mesajul default pentru reminder"""
        zile = (self.homework.deadline - self.data_reminder).days
        if zile == 0:
            return f"Azi trebuie să predai tema la {self.homework.subject.nume}: {self.homework.titlu}"
        elif zile == 1:
            return f"Mâine trebuie să predai tema la {self.homework.subject.nume}: {self.homework.titlu}"
        else:
            return f"În {zile} zile trebuie să predai tema la {self.homework.subject.nume}: {self.homework.titlu}"

    @property
    def mesaj_final(self):
        """Mesajul care va fi trimis (custom sau default)"""
        return self.mesaj_custom or self.mesaj_default