from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.subjects.models import Subject
from datetime import date


class Grade(models.Model):
    """
    Model pentru note și absențe
    """
    GRADE_TYPES = [
        ('nota', 'Notă'),
        ('absenta', 'Absență'),
        ('absenta_motivata', 'Absență motivată'),
        ('intarziere', 'Întârziere'),
    ]

    ASSESSMENT_TYPES = [
        ('oral', 'Recitare/Oral'),
        ('test', 'Test/Lucrare scrisă'),
        ('teza', 'Teză'),
        ('proiect', 'Proiect'),
        ('tema', 'Temă pentru acasă'),
        ('activitate', 'Activitate în clasă'),
        ('comportament', 'Comportament'),
        ('altele', 'Altele'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grade_set')

    # Tipul și valoarea
    tip = models.CharField(max_length=20, choices=GRADE_TYPES)
    valoare = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(1.0), MaxValueValidator(10.0)],
        blank=True,
        null=True,
        help_text="Valoarea notei (1.00 - 10.00). Nu se completează pentru absențe."
    )

    # Detalii evaluare
    tip_evaluare = models.CharField(
        max_length=20,
        choices=ASSESSMENT_TYPES,
        blank=True,
        help_text="Tipul de evaluare pentru note"
    )
    descriere = models.CharField(
        max_length=200,
        blank=True,
        help_text="Descrierea evaluării (ex: Capitolul 3, Ecuații de gradul 2)"
    )

    # Data și context
    data = models.DateField(default=date.today, help_text="Data când s-a primit nota/absența")
    semestru = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(2)],
        help_text="Semestrul (1 sau 2)"
    )

    # Pentru absențe
    motivata = models.BooleanField(
        default=False,
        help_text="Pentru absențe - dacă este motivată"
    )
    data_motivare = models.DateField(
        blank=True,
        null=True,
        help_text="Când a fost motivată absența"
    )

    # Note personale
    note_personale = models.TextField(
        blank=True,
        help_text="Note personale despre această evaluare"
    )

    # Pentru tracking progress
    importante = models.BooleanField(
        default=False,
        help_text="Notă importantă (teză, test important)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notă/Absență"
        verbose_name_plural = "Note/Absențe"
        ordering = ['-data', '-created_at']

    def __str__(self):
        if self.tip == 'nota':
            return f"{self.subject.nume} - {self.valoare} ({self.data})"
        else:
            status = "motivată" if self.motivata else "nemotivată"
            return f"{self.subject.nume} - {self.get_tip_display()} {status} ({self.data})"

    def clean(self):
        from django.core.exceptions import ValidationError

        # Validare: notele trebuie să aibă valoare, absențele nu
        if self.tip == 'nota' and not self.valoare:
            raise ValidationError("Notele trebuie să aibă o valoare.")

        if self.tip in ['absenta', 'absenta_motivata', 'intarziere'] and self.valoare:
            raise ValidationError("Absențele și întârzierile nu pot avea valoare numerică.")

        # Auto-setare tip pentru absențe motivate
        if self.tip == 'absenta' and self.motivata:
            self.tip = 'absenta_motivata'

    @property
    def culoare_afisare(self):
        """Returnează culoarea pentru afișare bazată pe valoare/tip"""
        if self.tip == 'nota':
            if self.valoare >= 9:
                return '#28a745'  # verde
            elif self.valoare >= 7:
                return '#ffc107'  # galben
            elif self.valoare >= 5:
                return '#fd7e14'  # portocaliu
            else:
                return '#dc3545'  # roșu
        elif self.tip in ['absenta', 'intarziere']:
            return '#dc3545' if not self.motivata else '#6c757d'
        else:
            return '#6c757d'  # gri

    @property
    def este_nota_mica(self):
        """Verifică dacă nota este sub 5"""
        return self.tip == 'nota' and self.valoare and self.valoare < 5

    @property
    def este_nota_mare(self):
        """Verifică dacă nota este peste 9"""
        return self.tip == 'nota' and self.valoare and self.valoare >= 9


class Semester(models.Model):
    """
    Configurație pentru semestre
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='semesters')

    # Detalii semestru
    numar = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(2)])
    an_scolar = models.CharField(max_length=10, help_text="Ex: 2024-2025")

    # Perioade
    data_inceput = models.DateField()
    data_sfarsit = models.DateField()

    # Status
    activ = models.BooleanField(default=False, help_text="Semestrul activ în prezent")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Semestru"
        verbose_name_plural = "Semestre"
        ordering = ['-an_scolar', '-numar']
        unique_together = ['user', 'numar', 'an_scolar']

    def __str__(self):
        return f"Semestrul {self.numar} - {self.an_scolar}"

    def save(self, *args, **kwargs):
        # Dacă se marchează ca activ, dezactivează toate celelalte semestre
        if self.activ:
            Semester.objects.filter(user=self.user).update(activ=False)
        super().save(*args, **kwargs)

    @property
    def este_in_desfasurare(self):
        """Verifică dacă semestrul este în desfășurare"""
        today = date.today()
        return self.data_inceput <= today <= self.data_sfarsit


class SubjectGradeStats(models.Model):
    """
    Statistici pentru note la o materie într-un semestru
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)

    # Statistici calculate
    media = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    numar_note = models.PositiveIntegerField(default=0)
    numar_absente = models.PositiveIntegerField(default=0)
    numar_absente_motivate = models.PositiveIntegerField(default=0)
    numar_intarzieri = models.PositiveIntegerField(default=0)

    # Note speciale
    nota_maxima = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    nota_minima = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    # Progres în timp
    tendinta = models.CharField(
        max_length=20,
        choices=[
            ('crescatoare', 'Crescătoare'),
            ('descrescatoare', 'Descrescătoare'),
            ('stabila', 'Stabilă'),
            ('neconcludenta', 'Neconcludentă'),
        ],
        default='neconcludenta'
    )

    # Ultima actualizare
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Statistici Note Materie"
        verbose_name_plural = "Statistici Note Materii"
        unique_together = ['user', 'subject', 'semester']

    def __str__(self):
        return f"{self.subject.nume} - {self.semester} - Media: {self.media or 'N/A'}"

    def calculeaza_statistici(self):
        """Recalculează toate statisticile pentru această materie în semestru"""
        # Notele din acest semestru
        note = Grade.objects.filter(
            user=self.user,
            subject=self.subject,
            tip='nota',
            semestru=self.semester.numar
        ).exclude(valoare__isnull=True).values_list('valoare', flat=True)

        if note:
            self.numar_note = len(note)
            self.media = sum(note) / len(note)
            self.nota_maxima = max(note)
            self.nota_minima = min(note)

            # Calculează tendința (pe ultimele 3 note)
            if len(note) >= 3:
                ultimele_note = list(note)[-3:]
                if ultimele_note[0] < ultimele_note[-1]:
                    self.tendinta = 'crescatoare'
                elif ultimele_note[0] > ultimele_note[-1]:
                    self.tendinta = 'descrescatoare'
                else:
                    self.tendinta = 'stabila'
        else:
            self.numar_note = 0
            self.media = None
            self.nota_maxima = None
            self.nota_minima = None
            self.tendinta = 'neconcludenta'

        # Absențe și întârzieri
        self.numar_absente = Grade.objects.filter(
            user=self.user,
            subject=self.subject,
            tip='absenta',
            semestru=self.semester.numar
        ).count()

        self.numar_absente_motivate = Grade.objects.filter(
            user=self.user,
            subject=self.subject,
            tip='absenta_motivata',
            semestru=self.semester.numar
        ).count()

        self.numar_intarzieri = Grade.objects.filter(
            user=self.user,
            subject=self.subject,
            tip='intarziere',
            semestru=self.semester.numar
        ).count()

        self.save()

    @property
    def total_absente(self):
        """Total absențe (motivate + nemotivate)"""
        return self.numar_absente + self.numar_absente_motivate

    @property
    def procent_absente(self):
        """Calculează procentul de absențe față de total ore"""
        # Estimare: ~18 săptămâni * ore pe săptămână
        ore_pe_saptamana = self.subject.ore_pe_saptamana
        if ore_pe_saptamana > 0:
            total_ore_estimate = 18 * ore_pe_saptamana
            return (self.total_absente / total_ore_estimate) * 100
        return 0

    @property
    def culoare_media(self):
        """Returnează culoarea pentru afișarea mediei"""
        if not self.media:
            return '#6c757d'

        if self.media >= 9:
            return '#28a745'
        elif self.media >= 7:
            return '#ffc107'
        elif self.media >= 5:
            return '#fd7e14'
        else:
            return '#dc3545'


class GradeGoal(models.Model):
    """
    Obiective de note pentru materii
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grade_goals')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grade_goals')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='grade_goals')

    # Obiectivul
    media_dorita = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(1.0), MaxValueValidator(10.0)],
        help_text="Media dorită pentru această materie"
    )

    # Context
    descriere = models.TextField(blank=True, help_text="De ce această medie este importantă")

    # Progress tracking
    atins = models.BooleanField(default=False)
    data_atins = models.DateField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Obiectiv Notă"
        verbose_name_plural = "Obiective Note"
        unique_together = ['user', 'subject', 'semester']

    def __str__(self):
        return f"{self.subject.nume} - Obiectiv: {self.media_dorita}"

    def verifica_obiectiv(self):
        """Verifică dacă obiectivul a fost atins"""
        try:
            stats = SubjectGradeStats.objects.get(
                user=self.user,
                subject=self.subject,
                semester=self.semester
            )
            if stats.media and stats.media >= self.media_dorita:
                if not self.atins:
                    self.atins = True
                    self.data_atins = date.today()
                    self.save()
                return True
            else:
                if self.atins:
                    self.atins = False
                    self.data_atins = None
                    self.save()
                return False
        except SubjectGradeStats.DoesNotExist:
            return False

    @property
    def diferenta_de_media(self):
        """Calculează diferența față de media actuală"""
        try:
            stats = SubjectGradeStats.objects.get(
                user=self.user,
                subject=self.subject,
                semester=self.semester
            )
            if stats.media:
                return float(self.media_dorita) - float(stats.media)
        except SubjectGradeStats.DoesNotExist:
            pass
        return float(self.media_dorita)  # Dacă nu are note încă

    @property
    def note_necesare(self):
        """Estimează câte note de 10 ar fi necesare pentru a atinge obiectivul"""
        try:
            stats = SubjectGradeStats.objects.get(
                user=self.user,
                subject=self.subject,
                semester=self.semester
            )
            if stats.media and stats.numar_note > 0:
                diferenta = self.diferenta_de_media
                if diferenta <= 0:
                    return 0

                # Calcul aproximativ: câte note de 10 sunt necesare
                suma_actuala = float(stats.media) * stats.numar_note
                note_necesare = 0

                while True:
                    note_necesare += 1
                    suma_noua = suma_actuala + 10  # adaugă o notă de 10
                    media_noua = suma_noua / (stats.numar_note + note_necesare)
                    if media_noua >= float(self.media_dorita):
                        break
                    suma_actuala = suma_noua
                    if note_necesare > 10:  # limitare pentru a evita loop infinit
                        break

                return note_necesare
        except SubjectGradeStats.DoesNotExist:
            pass
        return 1  # Estimare minimă