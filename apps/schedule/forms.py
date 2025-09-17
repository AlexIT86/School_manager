from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from datetime import time, timedelta
from .models import ScheduleEntry, ScheduleTemplate, ScheduleChange, ClassRoom, ClassScheduleEntry
from apps.subjects.models import Subject


class ScheduleEntryForm(forms.ModelForm):
    """Form pentru crearea și editarea intrărilor din orar"""

    class Meta:
        model = ScheduleEntry
        fields = ['subject', 'zi_saptamana', 'numar_ora', 'ora_inceput', 'ora_sfarsit', 'sala', 'tip_ora', 'note']
        labels = {
            'subject': 'Materia',
            'zi_saptamana': 'Ziua săptămânii',
            'numar_ora': 'Numărul orei',
            'ora_inceput': 'Ora de început',
            'ora_sfarsit': 'Ora de sfârșit',
            'sala': 'Sala',
            'tip_ora': 'Tipul orei',
            'note': 'Note speciale',
        }
        widgets = {
            'subject': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'zi_saptamana': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'numar_ora': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '8',
                'required': True
            }),
            'ora_inceput': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'required': True
            }),
            'ora_sfarsit': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'required': True
            }),
            'sala': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: A12, B5, Lab. Informatică'
            }),
            'tip_ora': forms.Select(attrs={
                'class': 'form-control'
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Note opționale...'
            }),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # păstrează user pe instanța formularului pentru validări ulterioare
        self.user = user

        # asigură-te că instanța are user setat înainte de validările ModelForm
        try:
            if user and not getattr(self.instance, 'user_id', None):
                self.instance.user = user
        except Exception:
            pass

        # Permite auto-completarea orelor în clean() fără erori de "required"
        if 'ora_inceput' in self.fields:
            self.fields['ora_inceput'].required = False
        if 'ora_sfarsit' in self.fields:
            self.fields['ora_sfarsit'].required = False

        if user:
            # Filtrează materiile pentru utilizatorul curent
            self.fields['subject'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')

        # Setează ore default bazate pe profilul utilizatorului
        if user and hasattr(user, 'student_profile') and not self.instance.pk:
            profile = user.student_profile
            if profile.ore_start:
                self.fields['ora_inceput'].initial = profile.ore_start
                # Calculează ora de sfârșit bazată pe durata orei
                start_time = profile.ore_start
                duration = timedelta(minutes=profile.durata_ora)
                end_time = (
                    time(start_time.hour, start_time.minute) + duration
                    if hasattr(time, '__add__') else
                    time((start_time.hour * 60 + start_time.minute + profile.durata_ora) // 60,
                         (start_time.hour * 60 + start_time.minute + profile.durata_ora) % 60)
                )
                self.fields['ora_sfarsit'].initial = end_time

        # Auto-completare sală din materie dacă există
        if self.instance.pk and self.instance.subject and self.instance.subject.sala:
            if not self.instance.sala:
                self.fields['sala'].initial = self.instance.subject.sala

    def clean(self):
        """Validări custom pentru formular"""
        cleaned_data = super().clean()
        zi_saptamana = cleaned_data.get('zi_saptamana')
        numar_ora = cleaned_data.get('numar_ora')
        ora_inceput = cleaned_data.get('ora_inceput')
        ora_sfarsit = cleaned_data.get('ora_sfarsit')

        # Completează automat orele dacă lipsesc, pe baza profilului și a numărului orei
        if (not ora_inceput or not ora_sfarsit) and numar_ora:
            try:
                from datetime import datetime, timedelta, time as time_cls
                if self.user and hasattr(self.user, 'student_profile') and self.user.student_profile:
                    base = self.user.student_profile.ore_start or time_cls(8, 0)
                    durata = getattr(self.user.student_profile, 'durata_ora', 50) or 50
                    pauza = getattr(self.user.student_profile, 'durata_pauza', 10) or 10
                else:
                    base = time_cls(8, 0)
                    durata = 50
                    pauza = 10

                offset = max(0, int(numar_ora) - 1) * (durata + pauza)
                start_dt = datetime.combine(datetime.today().date(), base) + timedelta(minutes=offset)
                end_dt = start_dt + timedelta(minutes=durata)
                cleaned_data['ora_inceput'] = start_dt.time()
                cleaned_data['ora_sfarsit'] = end_dt.time()
                ora_inceput = cleaned_data['ora_inceput']
                ora_sfarsit = cleaned_data['ora_sfarsit']
            except Exception:
                pass

        # Verifică dacă ora de sfârșit este după ora de început
        if ora_inceput and ora_sfarsit:
            if ora_sfarsit <= ora_inceput:
                raise ValidationError('Ora de sfârșit trebuie să fie după ora de început.')

        # Verifică suprapuneri doar dacă avem toate datele necesare
        if zi_saptamana and numar_ora and getattr(self, 'user', None):
            # Verifică dacă există deja o intrare la aceeași oră și zi
            existing = ScheduleEntry.objects.filter(
                user=self.user,
                zi_saptamana=zi_saptamana,
                numar_ora=numar_ora
            )

            # Exclude intrarea curentă dacă editează
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                existing_entry = existing.first()
                raise ValidationError(
                    f'Ora {numar_ora} din {self.get_weekday_name(zi_saptamana)} '
                    f'este deja ocupată de {existing_entry.subject.nume}.'
                )

        return cleaned_data

    def get_weekday_name(self, day_num):
        """Helper pentru numele zilei"""
        weekdays = {1: 'Luni', 2: 'Marți', 3: 'Miercuri', 4: 'Joi', 5: 'Vineri'}
        return weekdays.get(day_num, f'Ziua {day_num}')


class ScheduleTemplateForm(forms.ModelForm):
    """Form pentru template-urile de orar"""

    class Meta:
        model = ScheduleTemplate
        fields = ['nume', 'descriere']
        labels = {
            'nume': 'Numele template-ului',
            'descriere': 'Descriere',
        }
        widgets = {
            'nume': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Semestrul 1, Orarul de iarnă',
                'required': True
            }),
            'descriere': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descriere opțională pentru template...'
            }),
        }

    def clean_nume(self):
        """Validare nume template"""
        nume = self.cleaned_data['nume']
        if len(nume) < 3:
            raise ValidationError('Numele template-ului trebuie să aibă cel puțin 3 caractere.')
        return nume


class ScheduleChangeForm(forms.ModelForm):
    """Form pentru modificările în orar"""

    class Meta:
        model = ScheduleChange
        fields = [
            'schedule_entry', 'tip_schimbare', 'data_start', 'data_end',
            'motiv', 'ora_inceput_noua', 'ora_sfarsit_noua', 'sala_noua',
            'subject_nou', 'profesor_inlocuitor'
        ]
        labels = {
            'schedule_entry': 'Ora din orar',
            'tip_schimbare': 'Tipul modificării',
            'data_start': 'De la data',
            'data_end': 'Până la data (opțional)',
            'motiv': 'Motivul modificării',
            'ora_inceput_noua': 'Noua oră de început',
            'ora_sfarsit_noua': 'Noua oră de sfârșit',
            'sala_noua': 'Noua sală',
            'subject_nou': 'Noua materie',
            'profesor_inlocuitor': 'Profesor înlocuitor',
        }
        widgets = {
            'schedule_entry': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'tip_schimbare': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'data_start': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'data_end': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'motiv': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Profesor în concediu, Examen, Sărbătoare'
            }),
            'ora_inceput_noua': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'ora_sfarsit_noua': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'sala_noua': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Noua sală'
            }),
            'subject_nou': forms.Select(attrs={
                'class': 'form-control'
            }),
            'profesor_inlocuitor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numele profesorului înlocuitor'
            }),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            # Filtrează intrările din orar pentru utilizatorul curent
            self.fields['schedule_entry'].queryset = ScheduleEntry.objects.filter(
                user=user
            ).order_by('zi_saptamana', 'numar_ora')

            # Formatează afișarea intrărilor
            self.fields['schedule_entry'].label_from_instance = lambda obj: (
                f"{obj.get_zi_saptamana_display()} - Ora {obj.numar_ora}: {obj.subject.nume} "
                f"({obj.ora_inceput.strftime('%H:%M')} - {obj.ora_sfarsit.strftime('%H:%M')})"
            )

            # Filtrează materiile pentru înlocuiri
            self.fields['subject_nou'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')
            self.fields['subject_nou'].empty_label = "--- Selectează materia ---"

        # Setează data de start default la astăzi
        from datetime import date
        if not self.instance.pk:
            self.fields['data_start'].initial = date.today()

        # Organizează câmpurile în grupuri pentru template
        self.field_groups = [
            {
                'title': 'Informații de bază',
                'fields': ['schedule_entry', 'tip_schimbare', 'data_start', 'data_end', 'motiv'],
                'icon': 'fas fa-info-circle'
            },
            {
                'title': 'Modificări de timp (pentru ore mutate)',
                'fields': ['ora_inceput_noua', 'ora_sfarsit_noua'],
                'icon': 'fas fa-clock',
                'show_condition': 'mutata'
            },
            {
                'title': 'Modificări de locație/materie',
                'fields': ['sala_noua', 'subject_nou', 'profesor_inlocuitor'],
                'icon': 'fas fa-exchange-alt',
                'show_condition': 'inlocuita,sala_schimbata,profesor_inlocuitor'
            }
        ]

    def clean(self):
        """Validări custom pentru modificări"""
        cleaned_data = super().clean()
        tip_schimbare = cleaned_data.get('tip_schimbare')
        data_start = cleaned_data.get('data_start')
        data_end = cleaned_data.get('data_end')

        # Verifică dacă data de sfârșit este după data de început
        if data_start and data_end and data_end < data_start:
            raise ValidationError('Data de sfârșit trebuie să fie după data de început.')

        # Validări specifice pentru fiecare tip de schimbare
        if tip_schimbare == 'mutata':
            ora_inceput_noua = cleaned_data.get('ora_inceput_noua')
            ora_sfarsit_noua = cleaned_data.get('ora_sfarsit_noua')

            if not ora_inceput_noua or not ora_sfarsit_noua:
                raise ValidationError('Pentru ore mutate trebuie să specifici noile ore.')

            if ora_sfarsit_noua <= ora_inceput_noua:
                raise ValidationError('Ora de sfârșit trebuie să fie după ora de început.')

        elif tip_schimbare == 'inlocuita':
            subject_nou = cleaned_data.get('subject_nou')
            if not subject_nou:
                raise ValidationError('Pentru materie înlocuită trebuie să selectezi noua materie.')

        elif tip_schimbare == 'profesor_inlocuitor':
            profesor_inlocuitor = cleaned_data.get('profesor_inlocuitor')
            if not profesor_inlocuitor:
                raise ValidationError('Pentru profesor înlocuitor trebuie să specifici numele.')

        return cleaned_data


class QuickScheduleEntryForm(forms.Form):
    """Form rapid pentru adăugarea orelor din calendar"""

    subject = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        label='Materia'
    )

    zi_saptamana = forms.ChoiceField(
        choices=ScheduleEntry.WEEKDAYS,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        label='Ziua'
    )

    numar_ora = forms.IntegerField(
        min_value=1,
        max_value=8,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'min': '1',
            'max': '8'
        }),
        label='Ora'
    )

    sala = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Sala (opțional)'
        }),
        label='Sala'
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')


class ScheduleImportForm(forms.Form):
    """Form pentru importul orarului din fișier"""

    file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'xlsx', 'xls'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        }),
        label='Fișier orar',
        help_text='Format acceptat: CSV sau Excel cu coloane: Materie, Zi, Ora, Ora_Start, Ora_End, Sala'
    )

    clear_existing = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Șterge orarul existent',
        help_text='Elimină toate orele existente înainte de import'
    )

    create_subjects = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Creează materiile noi',
        help_text='Creează automat materiile care nu există'
    )


class ScheduleExportForm(forms.Form):
    """Form pentru exportul orarului"""

    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('xlsx', 'Excel (XLSX)'),
        ('pdf', 'PDF'),
        ('ics', 'Calendar (ICS)'),
    ]

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial='xlsx',
        widget=forms.RadioSelect(),
        label='Format export'
    )

    include_details = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Include detalii complete',
        help_text='Include sala, tipul orei și notele'
    )

    include_changes = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Include modificările active',
        help_text='Aplică modificările curente în export'
    )


class ScheduleSettingsForm(forms.Form):
    """Form pentru setările orarului"""

    ore_start = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        }),
        label='Ora de început a programului',
        initial=time(8, 0)
    )

    durata_ora = forms.IntegerField(
        min_value=30,
        max_value=90,
        initial=50,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '30',
            'max': '90',
            'step': '5'
        }),
        label='Durata unei ore (minute)'
    )

    durata_pauza = forms.IntegerField(
        min_value=5,
        max_value=30,
        initial=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '5',
            'max': '30',
            'step': '5'
        }),
        label='Durata pauzei (minute)'
    )

    nr_ore_pe_zi = forms.IntegerField(
        min_value=4,
        max_value=10,
        initial=7,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '4',
            'max': '10'
        }),
        label='Numărul maxim de ore pe zi'
    )

    show_weekend = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Afișează și weekendul',
        help_text='Include sâmbăta și duminica în calendar'
    )

    auto_calculate_times = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Calculează automat orele',
        help_text='Calculează automat ora de sfârșit bazată pe durata orei'
    )


class BulkScheduleActionForm(forms.Form):
    """Form pentru acțiuni în masă asupra orarului"""

    ACTION_CHOICES = [
        ('delete', 'Șterge orele selectate'),
        ('change_room', 'Schimbă sala'),
        ('copy_to_template', 'Copiază în template'),
        ('apply_changes', 'Aplică modificări'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Acțiune'
    )

    selected_entries = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    # Câmpuri condiționale
    new_room = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Noua sală'
        }),
        label='Noua sală'
    )

    template_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Numele template-ului'
        }),
        label='Numele template-ului'
    )

    def clean_selected_entries(self):
        """Validare și parsare ID-uri intrări selectate"""
        entries_str = self.cleaned_data['selected_entries']
        try:
            entry_ids = [int(id) for id in entries_str.split(',') if id.strip()]
            if not entry_ids:
                raise forms.ValidationError('Nu ai selectat nicio oră.')
            return entry_ids
        except ValueError:
            raise forms.ValidationError('ID-uri invalide pentru ore.')

    def clean(self):
        """Validare cross-field"""
        cleaned_data = super().clean()
        action = cleaned_data.get('action')

        if action == 'change_room' and not cleaned_data.get('new_room'):
            raise forms.ValidationError('Trebuie să specifici noua sală.')

        if action == 'copy_to_template' and not cleaned_data.get('template_name'):
            raise forms.ValidationError('Trebuie să specifici numele template-ului.')

        return cleaned_data


class ClassRoomForm(forms.ModelForm):
    """Form pentru clase (6A, 7B)"""

    class Meta:
        model = ClassRoom
        fields = ['nume', 'scoala', 'diriginte', 'descriere']
        labels = {
            'nume': 'Clasa',
            'scoala': 'Școala',
            'diriginte': 'Diriginte (utilizator)',
            'descriere': 'Descriere',
        }
        widgets = {
            'nume': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex: 6A', 'required': True}),
            'scoala': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex: Liceul ...'}),
            'diriginte': forms.Select(attrs={'class': 'form-control'}),
            'descriere': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ClassScheduleEntryForm(forms.ModelForm):
    """Form pentru intrările de orar la nivel de clasă"""

    class Meta:
        model = ClassScheduleEntry
        fields = [
            'zi_saptamana', 'numar_ora', 'ora_inceput', 'ora_sfarsit',
            'subject_name', 'subject_color', 'sala', 'tip_ora', 'note'
        ]
        labels = {
            'zi_saptamana': 'Ziua',
            'numar_ora': 'Ora (index)',
            'ora_inceput': 'Început',
            'ora_sfarsit': 'Sfârșit',
            'subject_name': 'Materia',
            'subject_color': 'Culoare',
            'sala': 'Sala',
            'tip_ora': 'Tipul orei',
            'note': 'Note',
        }
        widgets = {
            'zi_saptamana': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'numar_ora': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '8', 'required': True}),
            'ora_inceput': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'required': True}),
            'ora_sfarsit': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time', 'required': True}),
            'subject_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex: Matematică', 'required': True}),
            'subject_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color', 'style': 'height: 45px;'}),
            'sala': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex: A12'}),
            'tip_ora': forms.Select(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('ora_inceput')
        end = cleaned.get('ora_sfarsit')
        if start and end and end <= start:
            raise ValidationError('Ora de sfârșit trebuie să fie după ora de început.')
        return cleaned