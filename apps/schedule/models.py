from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from apps.subjects.models import Subject


class ScheduleEntry(models.Model):
    """
    O intrare în orarul școlar - o oră la o anumită materie
    """
    WEEKDAYS = [
        (1, 'Luni'),
        (2, 'Marți'),
        (3, 'Miercuri'),
        (4, 'Joi'),
        (5, 'Vineri'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedule_entries')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='schedule_entries')

    # Programare
    zi_saptamana = models.IntegerField(choices=WEEKDAYS, help_text="1=Luni, 2=Marți, etc.")
    ora_inceput = models.TimeField(help_text="Ora de început")
    ora_sfarsit = models.TimeField(help_text="Ora de sfârșit")

    # Detalii suplimentare
    sala = models.CharField(max_length=20, blank=True, help_text="Sala specifică pentru această oră")
    note = models.TextField(blank=True, help_text="Note speciale pentru această oră")

    # Numărul orei în ziua respectivă (pentru ordonare)
    numar_ora = models.PositiveIntegerField(help_text="A câta oră din zi (1, 2, 3, etc.)")

    # Tipul orei
    tip_ora = models.CharField(
        max_length=20,
        choices=[
            ('normal', 'Oră normală'),
            ('dirigentie', 'Ora de dirigentie'),
            ('optionala', 'Oră opțională'),
            ('recuperare', 'Oră de recuperare'),
        ],
        default='normal'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Intrare Orar"
        verbose_name_plural = "Intrări Orar"
        ordering = ['zi_saptamana', 'numar_ora']
        unique_together = ['user', 'zi_saptamana', 'numar_ora']  # Nu poate avea două ore la același interval

    def __str__(self):
        return f"{self.get_zi_saptamana_display()} - Ora {self.numar_ora}: {self.subject.nume}"

    def clean(self):
        """Validări personalizate"""
        if self.ora_inceput >= self.ora_sfarsit:
            raise ValidationError("Ora de început trebuie să fie înainte de ora de sfârșit")

        # Verifică să nu se suprapună cu alte ore în aceeași zi
        conflicting_entries = ScheduleEntry.objects.filter(
            user=self.user,
            zi_saptamana=self.zi_saptamana
        ).exclude(pk=self.pk)

        for entry in conflicting_entries:
            if (self.ora_inceput < entry.ora_sfarsit and self.ora_sfarsit > entry.ora_inceput):
                raise ValidationError(
                    f"Se suprapune cu {entry.subject.nume} "
                    f"({entry.ora_inceput.strftime('%H:%M')} - {entry.ora_sfarsit.strftime('%H:%M')})"
                )

    @property
    def durata_minunte(self):
        """Calculează durata orei în minute"""
        from datetime import datetime, timedelta
        start = datetime.combine(datetime.today(), self.ora_inceput)
        end = datetime.combine(datetime.today(), self.ora_sfarsit)
        return int((end - start).total_seconds() / 60)


class ClassRoom(models.Model):
    """
    Reprezintă o clasă (ex: 6A, 7B) pentru care se poate defini un orar comun.
    """
    nume = models.CharField(max_length=20, unique=True, help_text="Ex: 6A, 7B")
    scoala = models.CharField(max_length=200, blank=True)
    judet = models.CharField(max_length=50, blank=True, help_text="Județul școlii (ex: București, Cluj)")
    diriginte = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes_led')
    descriere = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Clasă"
        verbose_name_plural = "Clase"
        ordering = ['nume']

    def __str__(self):
        return self.nume


class ClassScheduleEntry(models.Model):
    """
    O intrare de orar definită la nivel de clasă (independentă de utilizatori).
    Nu depinde de modelul Subject (care este per utilizator). Reține numele materiei
    și culoarea, care vor fi mapate/creată materia la preluare de către elev.
    """
    class_room = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='schedule_entries')

    zi_saptamana = models.IntegerField(choices=ScheduleEntry.WEEKDAYS, help_text="1=Luni, 2=Marți, etc.")
    numar_ora = models.PositiveIntegerField(help_text="A câta oră din zi (1, 2, 3, etc.)")
    ora_inceput = models.TimeField()
    ora_sfarsit = models.TimeField()

    subject_name = models.CharField(max_length=100, help_text="Numele materiei (ex: Matematică)")
    subject_color = models.CharField(max_length=7, default='#007bff', help_text="Culoare în format hex (#FF5733)")

    sala = models.CharField(max_length=20, blank=True)
    note = models.TextField(blank=True)
    tip_ora = models.CharField(
        max_length=20,
        choices=[
            ('normal', 'Oră normală'),
            ('dirigentie', 'Ora de dirigentie'),
            ('optionala', 'Oră opțională'),
            ('recuperare', 'Oră de recuperare'),
        ],
        default='normal'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Intrare Orar Clasă"
        verbose_name_plural = "Intrări Orar Clasă"
        ordering = ['class_room', 'zi_saptamana', 'numar_ora']
        unique_together = ['class_room', 'zi_saptamana', 'numar_ora']

    def __str__(self):
        return f"{self.class_room.nume} - {self.get_zi_saptamana_display()} Ora {self.numar_ora}: {self.subject_name}"


def apply_class_schedule_to_user(class_room: 'ClassRoom', user: User) -> int:
    """
    Copiază orarul definit la nivelul clasei în orarul utilizatorului dat.
    Returnează numărul de intrări create. Dacă utilizatorul are deja orar, nu suprascrie.
    """
    # Nu suprascriem dacă are deja orar definit
    if ScheduleEntry.objects.filter(user=user).exists():
        return 0

    created = 0
    # Pentru calculul orelor, folosim orele din intrările de clasă
    for e in ClassScheduleEntry.objects.filter(class_room=class_room).order_by('zi_saptamana', 'numar_ora'):
        try:
            # Găsește sau creează materia pentru utilizator
            subject, _ = Subject.objects.get_or_create(
                user=user,
                nume=e.subject_name,
                defaults={'culoare': e.subject_color, 'activa': True}
            )

            ScheduleEntry.objects.create(
                user=user,
                subject=subject,
                zi_saptamana=e.zi_saptamana,
                ora_inceput=e.ora_inceput,
                ora_sfarsit=e.ora_sfarsit,
                sala=e.sala,
                note=e.note,
                numar_ora=e.numar_ora,
                tip_ora=e.tip_ora,
            )
            created += 1
        except Exception:
            # Ignoră intrările problematice pentru a continua procesul
            continue

    return created

class ScheduleTemplate(models.Model):
    """
    Template-uri pentru orar (ex: pentru semestre diferite)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedule_templates')
    nume = models.CharField(max_length=100, help_text="Ex: Semestrul 1, Semestrul 2")
    descriere = models.TextField(blank=True)

    # Status
    activ = models.BooleanField(default=False, help_text="Template-ul activ în prezent")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Template Orar"
        verbose_name_plural = "Template-uri Orar"
        ordering = ['-activ', '-updated_at']

    def __str__(self):
        return f"{self.nume} {'(Activ)' if self.activ else ''}"

    def save(self, *args, **kwargs):
        # Dacă se marchează ca activ, dezactivează toate celelalte template-uri
        if self.activ:
            ScheduleTemplate.objects.filter(user=self.user).update(activ=False)
        super().save(*args, **kwargs)

    def aplicare_template(self):
        """Aplică acest template la orarul curent"""
        # Șterge orarul curent
        ScheduleEntry.objects.filter(user=self.user).delete()

        # Copiază intrările din template
        for template_entry in self.template_entries.all():
            ScheduleEntry.objects.create(
                user=self.user,
                subject=template_entry.subject,
                zi_saptamana=template_entry.zi_saptamana,
                ora_inceput=template_entry.ora_inceput,
                ora_sfarsit=template_entry.ora_sfarsit,
                sala=template_entry.sala,
                note=template_entry.note,
                numar_ora=template_entry.numar_ora,
                tip_ora=template_entry.tip_ora,
            )

        # Marchează template-ul ca activ
        ScheduleTemplate.objects.filter(user=self.user).update(activ=False)
        self.activ = True
        self.save()


class ScheduleTemplateEntry(models.Model):
    """
    Intrări în template-urile de orar
    """
    template = models.ForeignKey(ScheduleTemplate, on_delete=models.CASCADE, related_name='template_entries')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    # Aceleași câmpuri ca ScheduleEntry
    zi_saptamana = models.IntegerField(choices=ScheduleEntry.WEEKDAYS)
    ora_inceput = models.TimeField()
    ora_sfarsit = models.TimeField()
    sala = models.CharField(max_length=20, blank=True)
    note = models.TextField(blank=True)
    numar_ora = models.PositiveIntegerField()
    tip_ora = models.CharField(
        max_length=20,
        choices=[
            ('normal', 'Oră normală'),
            ('dirigentie', 'Ora de dirigentie'),
            ('optionala', 'Oră opțională'),
            ('recuperare', 'Oră de recuperare'),
        ],
        default='normal'
    )

    class Meta:
        verbose_name = "Intrare Template Orar"
        verbose_name_plural = "Intrări Template Orar"
        ordering = ['zi_saptamana', 'numar_ora']
        unique_together = ['template', 'zi_saptamana', 'numar_ora']

    def __str__(self):
        return f"{self.template.nume} - {self.get_zi_saptamana_display()} Ora {self.numar_ora}: {self.subject.nume}"


class ScheduleChange(models.Model):
    """
    Modificări temporare în orar (ore mutate, anulate, etc.)
    """
    CHANGE_TYPES = [
        ('anulata', 'Oră anulată'),
        ('mutata', 'Oră mutată'),
        ('inlocuita', 'Materie înlocuită'),
        ('sala_schimbata', 'Sala schimbată'),
        ('profesor_inlocuitor', 'Profesor înlocuitor'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedule_changes')
    schedule_entry = models.ForeignKey(ScheduleEntry, on_delete=models.CASCADE, related_name='changes')

    # Tipul schimbării
    tip_schimbare = models.CharField(max_length=20, choices=CHANGE_TYPES)

    # Datele pentru care se aplică schimbarea
    data_start = models.DateField(help_text="De la această dată")
    data_end = models.DateField(blank=True, null=True, help_text="Până la această dată (opțional)")

    # Detalii schimbare
    motiv = models.CharField(max_length=200, blank=True, help_text="Motivul schimbării")

    # Valori noi (pentru ore mutate/înlocuite)
    ora_inceput_noua = models.TimeField(blank=True, null=True)
    ora_sfarsit_noua = models.TimeField(blank=True, null=True)
    sala_noua = models.CharField(max_length=20, blank=True)
    subject_nou = models.ForeignKey(Subject, on_delete=models.CASCADE, blank=True, null=True,
                                    related_name='schedule_changes_new')
    profesor_inlocuitor = models.CharField(max_length=100, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Schimbare Orar"
        verbose_name_plural = "Schimbări Orar"
        ordering = ['-data_start']

    def __str__(self):
        return f"{self.get_tip_schimbare_display()} - {self.schedule_entry.subject.nume} ({self.data_start})"

    def este_activa(self, data=None):
        """Verifică dacă schimbarea este activă pentru o anumită dată"""
        if data is None:
            from datetime import date
            data = date.today()

        if data < self.data_start:
            return False

        if self.data_end and data > self.data_end:
            return False

        return True