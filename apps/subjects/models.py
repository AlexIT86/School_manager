from django.db import models
from django.contrib.auth.models import User
import os


def subject_file_upload_path(instance, filename):
    """Generează calea pentru fișierele uploadate la materii"""
    return f'subjects/{instance.subject.id}/{filename}'


class Subject(models.Model):
    """
    Model pentru materii/discipline școlare
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    nume = models.CharField(max_length=100, help_text="Ex: Matematică, Română, Engleză")
    nume_profesor = models.CharField(max_length=100, blank=True)
    sala = models.CharField(max_length=20, blank=True, help_text="Ex: A1, B5, etc.")

    # Culoare pentru calendar și organizare
    culoare = models.CharField(
        max_length=7,
        default='#007bff',
        help_text="Culoare în format hex (#FF5733)"
    )

    # Descriere și note
    descriere = models.TextField(blank=True, help_text="Note despre materie")

    # Manual și resurse
    manual = models.CharField(max_length=200, blank=True, help_text="Numele manualului folosit")

    # Status
    activa = models.BooleanField(default=True, help_text="Materia se mai studiază în acest semestru")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Materie"
        verbose_name_plural = "Materii"
        ordering = ['nume']
        unique_together = ['user', 'nume']  # Un user nu poate avea două materii cu același nume

    def __str__(self):
        return self.nume

    @property
    def ore_pe_saptamana(self):
        """Calculează câte ore pe săptămână are materia în orar"""
        from apps.schedule.models import ScheduleEntry
        return ScheduleEntry.objects.filter(subject=self).count()

    @property
    def teme_active(self):
        """Returnează temele nefinalizate pentru această materie"""
        from apps.homework.models import Homework
        return self.homework_set.filter(finalizata=False)

    @property
    def media_note(self):
        """Calculează media notelor la această materie"""
        from apps.grades.models import Grade
        note = self.grade_set.filter(tip='nota').values_list('valoare', flat=True)
        if note:
            return sum(note) / len(note)
        return None

    @property
    def numar_absente(self):
        """Numără absențele la această materie"""
        from apps.grades.models import Grade
        return self.grade_set.filter(tip='absenta').count()


class SubjectFile(models.Model):
    """
    Fișiere uploadate pentru o materie (poze, documente, etc.)
    """
    FILE_TYPES = [
        ('document', 'Document'),
        ('imagine', 'Imagine'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('altele', 'Altele'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='files')
    nume = models.CharField(max_length=200, help_text="Numele afișat pentru fișier")
    fisier = models.FileField(upload_to=subject_file_upload_path)
    tip = models.CharField(max_length=20, choices=FILE_TYPES, default='document')
    descriere = models.TextField(blank=True)

    # Metadata
    marime = models.PositiveIntegerField(null=True, blank=True, help_text="Mărime în bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fișier Materie"
        verbose_name_plural = "Fișiere Materii"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.subject.nume} - {self.nume}"

    def save(self, *args, **kwargs):
        if self.fisier:
            # Setează mărimea fișierului
            self.marime = self.fisier.size

            # Detectează tipul fișierului din extensie
            _, ext = os.path.splitext(self.fisier.name.lower())
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                self.tip = 'imagine'
            elif ext in ['.mp3', '.wav', '.ogg', '.m4a']:
                self.tip = 'audio'
            elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv']:
                self.tip = 'video'
            elif ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt']:
                self.tip = 'document'
            else:
                self.tip = 'altele'

        super().save(*args, **kwargs)

    @property
    def marime_formatata(self):
        """Returnează mărimea fișierului în format human-readable"""
        if not self.marime:
            return "Necunoscut"

        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.marime < 1024.0:
                return f"{self.marime:.1f} {unit}"
            self.marime /= 1024.0
        return f"{self.marime:.1f} TB"

    @property
    def extensie(self):
        """Returnează extensia fișierului"""
        if self.fisier:
            _, ext = os.path.splitext(self.fisier.name)
            return ext.lower()
        return ""


class SubjectNote(models.Model):
    """
    Notițe personale pentru o materie
    """
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='notes')
    titlu = models.CharField(max_length=200)
    continut = models.TextField()

    # Organizare
    important = models.BooleanField(default=False, help_text="Notița este importantă")
    tags = models.CharField(max_length=200, blank=True, help_text="Tag-uri separate prin virgulă")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notiță Materie"
        verbose_name_plural = "Notițe Materii"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.subject.nume} - {self.titlu}"

    @property
    def tag_list(self):
        """Returnează o listă cu tag-urile"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []