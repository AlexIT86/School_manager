from django import forms
from django.core.validators import FileExtensionValidator
from django.conf import settings
from datetime import date, timedelta
from .models import Homework, HomeworkFile, HomeworkSession, HomeworkReminder
from apps.subjects.models import Subject


class HomeworkForm(forms.ModelForm):
    """Form pentru crearea și editarea temelor"""

    class Meta:
        model = Homework
        fields = [
            'subject', 'titlu', 'descriere', 'pagini', 'exercitii',
            'data_primita', 'deadline', 'prioritate', 'dificultate',
            'timp_estimat', 'reminder_activ', 'zile_reminder', 'note_personale'
        ]
        labels = {
            'subject': 'Materia',
            'titlu': 'Titlul temei',
            'descriere': 'Descrierea temei',
            'pagini': 'Pagini/Capitole',
            'exercitii': 'Exercițiile de făcut',
            'data_primita': 'Data când a fost dată tema',
            'deadline': 'Data limită',
            'prioritate': 'Prioritatea',
            'dificultate': 'Dificultatea estimată',
            'timp_estimat': 'Timp estimat (minute)',
            'reminder_activ': 'Activează reminder',
            'zile_reminder': 'Cu câte zile înainte să anunțe',
            'note_personale': 'Notițe personale',
        }
        widgets = {
            'subject': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'titlu': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Exercițiile 1-10 de la pagina 25',
                'required': True
            }),
            'descriere': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrierea detaliată a temei...',
                'required': True
            }),
            'pagini': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: pag. 25-30, cap. 3'
            }),
            'exercitii': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detalii despre exercițiile de făcut...'
            }),
            'data_primita': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'prioritate': forms.Select(attrs={
                'class': 'form-control'
            }),
            'dificultate': forms.Select(attrs={
                'class': 'form-control'
            }),
            'timp_estimat': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '5',
                'max': '600',
                'step': '5',
                'placeholder': 'minute'
            }),
            'reminder_activ': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'zile_reminder': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '7'
            }),
            'note_personale': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notițe personale despre această temă...'
            }),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            # Filtrează materiile pentru utilizatorul curent
            self.fields['subject'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')

        # Setează valori default
        if not self.instance.pk:  # Doar pentru forme noi
            self.fields['data_primita'].initial = date.today()
            self.fields['deadline'].initial = date.today() + timedelta(days=1)
            self.fields['prioritate'].initial = 'normala'
            self.fields['dificultate'].initial = 'medie'
            self.fields['reminder_activ'].initial = True
            self.fields['zile_reminder'].initial = 1

    def clean_deadline(self):
        """Validare deadline"""
        deadline = self.cleaned_data['deadline']
        data_primita = self.cleaned_data.get('data_primita')

        if deadline < date.today():
            raise forms.ValidationError('Data limită nu poate fi în trecut.')

        if data_primita and deadline < data_primita:
            raise forms.ValidationError('Data limită nu poate fi înainte de data când a fost dată tema.')

        return deadline

    def clean_timp_estimat(self):
        """Validare timp estimat"""
        timp = self.cleaned_data.get('timp_estimat')
        if timp and timp < 5:
            raise forms.ValidationError('Timpul estimat trebuie să fie cel puțin 5 minute.')
        return timp


class HomeworkFileForm(forms.ModelForm):
    """Form pentru upload fișiere la teme"""

    class Meta:
        model = HomeworkFile
        fields = ['nume', 'fisier', 'tip', 'descriere']
        labels = {
            'nume': 'Numele fișierului',
            'fisier': 'Selectează fișierul',
            'tip': 'Tipul fișierului',
            'descriere': 'Descriere',
        }
        widgets = {
            'nume': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Soluția exercițiului 1, Rezumat capitol'
            }),
            'fisier': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': ','.join([f'.{ext}' for ext in getattr(settings, 'ALLOWED_FILE_EXTENSIONS', [
                    'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif',
                    'mp3', 'mp4', 'avi', 'mov', 'zip', 'rar'
                ])])
            }),
            'tip': forms.Select(attrs={
                'class': 'form-control'
            }),
            'descriere': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Descriere opțională...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Validatori pentru fișier
        allowed_extensions = getattr(settings, 'ALLOWED_FILE_EXTENSIONS', [
            'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif',
            'mp3', 'mp4', 'avi', 'mov', 'zip', 'rar'
        ])

        self.fields['fisier'].validators.append(
            FileExtensionValidator(allowed_extensions=allowed_extensions)
        )

    def clean_fisier(self):
        """Validare mărime fișier"""
        fisier = self.cleaned_data['fisier']
        if fisier:
            max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 10 * 1024 * 1024)
            if fisier.size > max_size:
                max_size_mb = max_size / (1024 * 1024)
                raise forms.ValidationError(f'Fișierul este prea mare. Mărimea maximă: {max_size_mb:.1f}MB.')
        return fisier


class HomeworkSessionForm(forms.ModelForm):
    """Form pentru sesiunile de lucru"""

    class Meta:
        model = HomeworkSession
        fields = ['note_sesiune', 'dificultati_sesiune', 'progres_dupa']
        labels = {
            'note_sesiune': 'Ce ai făcut în această sesiune',
            'dificultati_sesiune': 'Dificultăți întâmpinate',
            'progres_dupa': 'Progresul după această sesiune (%)',
        }
        widgets = {
            'note_sesiune': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrie ce ai lucrat în această sesiune...'
            }),
            'dificultati_sesiune': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Probleme sau dificultăți întâmpinate...'
            }),
            'progres_dupa': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '5'
            }),
        }

    def clean_progres_dupa(self):
        """Validare progres"""
        progres = self.cleaned_data.get('progres_dupa')
        if progres is not None:
            if progres < 0 or progres > 100:
                raise forms.ValidationError('Progresul trebuie să fie între 0 și 100%.')
        return progres


class HomeworkFilterForm(forms.Form):
    """Form pentru filtrarea temelor"""

    STATUS_CHOICES = [
        ('', 'Toate'),
        ('active', 'Active'),
        ('completed', 'Finalizate'),
        ('overdue', 'Întârziate'),
    ]

    DEADLINE_CHOICES = [
        ('', 'Oricând'),
        ('today', 'Astăzi'),
        ('tomorrow', 'Mâine'),
        ('this_week', 'Săptămâna aceasta'),
        ('next_week', 'Săptămâna viitoare'),
    ]

    subject = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label='Toate materiile',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Materia'
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Status'
    )

    priority = forms.ChoiceField(
        choices=[('', 'Toate prioritățile')] + Homework.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Prioritatea'
    )

    deadline_range = forms.ChoiceField(
        choices=DEADLINE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Deadline'
    )

    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Caută în titlu, descriere, materie...',
            'type': 'search'
        }),
        label='Căutare'
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')


class QuickHomeworkForm(forms.Form):
    """Form rapid pentru adăugarea temelor din dashboard"""

    subject = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        label='Materia'
    )

    titlu = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Titlul temei...'
        }),
        label='Temă'
    )

    deadline = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date'
        }),
        label='Deadline'
    )

    prioritate = forms.ChoiceField(
        choices=Homework.PRIORITY_CHOICES,
        initial='normala',
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        label='Prioritate'
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')

        # Setează deadline default la mâine
        self.fields['deadline'].initial = date.today() + timedelta(days=1)


class HomeworkReminderForm(forms.ModelForm):
    """Form pentru crearea reminder-urilor personalizate"""

    class Meta:
        model = HomeworkReminder
        fields = ['data_reminder', 'ora_reminder', 'mesaj_custom']
        labels = {
            'data_reminder': 'Data reminder-ului',
            'ora_reminder': 'Ora reminder-ului',
            'mesaj_custom': 'Mesaj personalizat (opțional)',
        }
        widgets = {
            'data_reminder': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'ora_reminder': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'mesaj_custom': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Mesaj personalizat pentru reminder (opțional)...'
            }),
        }

    def __init__(self, homework=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.homework = homework

        if homework and not self.instance.pk:
            # Setează data default cu o zi înainte de deadline
            if homework.deadline > date.today():
                self.fields['data_reminder'].initial = homework.deadline - timedelta(days=1)
            else:
                self.fields['data_reminder'].initial = date.today()

    def clean_data_reminder(self):
        """Validare dată reminder"""
        data_reminder = self.cleaned_data['data_reminder']

        if data_reminder < date.today():
            raise forms.ValidationError('Data reminder-ului nu poate fi în trecut.')

        if self.homework and data_reminder > self.homework.deadline:
            raise forms.ValidationError('Reminder-ul nu poate fi după deadline-ul temei.')

        return data_reminder


class HomeworkProgressForm(forms.Form):
    """Form pentru actualizarea rapidă a progresului"""

    progress = forms.IntegerField(
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'type': 'range',
            'step': '5'
        }),
        label='Progres (%)'
    )

    note = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Notițe despre progres (opțional)...'
        }),
        label='Notițe'
    )


class BulkHomeworkActionForm(forms.Form):
    """Form pentru acțiuni în masă asupra temelor"""

    ACTION_CHOICES = [
        ('complete', 'Marchează ca finalizate'),
        ('incomplete', 'Marchează ca nefinalizate'),
        ('delete', 'Șterge temele selectate'),
        ('change_priority', 'Schimbă prioritatea'),
        ('extend_deadline', 'Prelungește deadline-ul'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Acțiune'
    )

    selected_homework = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    # Câmpuri condiționale pentru acțiuni specifice
    new_priority = forms.ChoiceField(
        choices=Homework.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Noua prioritate'
    )

    extend_days = forms.IntegerField(
        min_value=1,
        max_value=30,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Numărul de zile'
        }),
        label='Prelungește cu (zile)'
    )

    def clean_selected_homework(self):
        """Validare și parsare ID-uri teme selectate"""
        homework_str = self.cleaned_data['selected_homework']
        try:
            homework_ids = [int(id) for id in homework_str.split(',') if id.strip()]
            if not homework_ids:
                raise forms.ValidationError('Nu ai selectat nicio temă.')
            return homework_ids
        except ValueError:
            raise forms.ValidationError('ID-uri invalide pentru teme.')

    def clean(self):
        """Validare cross-field"""
        cleaned_data = super().clean()
        action = cleaned_data.get('action')

        if action == 'change_priority' and not cleaned_data.get('new_priority'):
            raise forms.ValidationError('Trebuie să selectezi o prioritate nouă.')

        if action == 'extend_deadline' and not cleaned_data.get('extend_days'):
            raise forms.ValidationError('Trebuie să specifici cu câte zile să prelungești.')

        return cleaned_data


class HomeworkImportForm(forms.Form):
    """Form pentru importul temelor din fișier"""

    file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'xlsx', 'xls'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        }),
        label='Fișier import',
        help_text='Format acceptat: CSV sau Excel cu coloane: Materie, Titlu, Descriere, Deadline, Prioritate'
    )

    overwrite_existing = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Suprascrie temele existente',
        help_text='Dacă o temă cu același titlu și materie există, o va actualiza'
    )