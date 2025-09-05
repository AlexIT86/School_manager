from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import StudentProfile


class UserRegistrationForm(UserCreationForm):
    """Form pentru înregistrarea utilizatorilor"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label="Prenume")
    last_name = forms.CharField(max_length=30, required=True, label="Nume")

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        labels = {
            'username': 'Nume utilizator',
        }
        help_texts = {
            'username': 'Obligatoriu. 150 caractere sau mai puține. Doar litere, cifre și @/./+/-/_ sunt permise.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Adaugă clase CSS Bootstrap
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

        # Placeholder-uri
        self.fields['username'].widget.attrs['placeholder'] = 'ex: ion_popescu'
        self.fields['first_name'].widget.attrs['placeholder'] = 'Ion'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Popescu'
        self.fields['email'].widget.attrs['placeholder'] = 'ion@example.com'
        self.fields['password1'].widget.attrs['placeholder'] = 'Parola ta'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirmă parola'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class StudentProfileForm(forms.ModelForm):
    """Form pentru configurarea profilului de student"""

    class Meta:
        model = StudentProfile
        fields = [
            'clasa', 'scoala', 'telefon_parinte', 'email_parinte',
            'ore_start', 'durata_ora', 'durata_pauza', 'nr_ore_pe_zi',
            'reminder_teme', 'reminder_note', 'zile_reminder_teme'
        ]
        labels = {
            'clasa': 'Clasa',
            'scoala': 'Școala',
            'telefon_parinte': 'Telefon părinte',
            'email_parinte': 'Email părinte',
            'ore_start': 'Ora de început a programului',
            'durata_ora': 'Durata unei ore (minute)',
            'durata_pauza': 'Durata pauzei (minute)',
            'nr_ore_pe_zi': 'Numărul maxim de ore pe zi',
            'reminder_teme': 'Activează reminder-uri pentru teme',
            'reminder_note': 'Activează reminder-uri pentru note noi',
            'zile_reminder_teme': 'Cu câte zile înainte să anunțe temele',
        }
        widgets = {
            'clasa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: 6A, 7B'
            }),
            'scoala': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Liceul Teoretic "Mihai Eminescu"'
            }),
            'telefon_parinte': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: 0712345678'
            }),
            'email_parinte': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: parinte@email.com'
            }),
            'ore_start': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'durata_ora': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '30',
                'max': '60',
                'step': '5'
            }),
            'durata_pauza': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '5',
                'max': '30',
                'step': '5'
            }),
            'nr_ore_pe_zi': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '4',
                'max': '8'
            }),
            'reminder_teme': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'reminder_note': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'zile_reminder_teme': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '7'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Grupează câmpurile pentru organizare în template
        self.field_groups = [
            {
                'title': 'Informații personale',
                'fields': ['clasa', 'scoala'],
                'icon': 'fas fa-user-graduate'
            },
            {
                'title': 'Contact părinte',
                'fields': ['telefon_parinte', 'email_parinte'],
                'icon': 'fas fa-phone'
            },
            {
                'title': 'Configurare orar',
                'fields': ['ore_start', 'durata_ora', 'durata_pauza', 'nr_ore_pe_zi'],
                'icon': 'fas fa-clock'
            },
            {
                'title': 'Notificări',
                'fields': ['reminder_teme', 'reminder_note', 'zile_reminder_teme'],
                'icon': 'fas fa-bell'
            }
        ]


class QuickHomeworkForm(forms.Form):
    """Form rapid pentru adăugarea temelor din dashboard"""
    subject = forms.ModelChoiceField(
        queryset=None,  # Va fi setat în __init__
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Materia'
    )
    titlu = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ex: Exercițiile 1-5 de la pagina 25'
        }),
        label='Titlu temă'
    )
    deadline = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data limită'
    )
    prioritate = forms.ChoiceField(
        choices=[
            ('normala', 'Normală'),
            ('ridicata', 'Ridicată'),
            ('urgenta', 'Urgentă'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='normala',
        label='Prioritate'
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from apps.subjects.models import Subject
            self.fields['subject'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')


class QuickGradeForm(forms.Form):
    """Form rapid pentru adăugarea notelor din dashboard"""
    subject = forms.ModelChoiceField(
        queryset=None,  # Va fi setat în __init__
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Materia'
    )
    valoare = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        min_value=1.0,
        max_value=10.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.25',
            'min': '1',
            'max': '10'
        }),
        label='Nota'
    )
    tip_evaluare = forms.ChoiceField(
        choices=[
            ('oral', 'Recitare/Oral'),
            ('test', 'Test/Lucrare scrisă'),
            ('teza', 'Teză'),
            ('proiect', 'Proiect'),
            ('tema', 'Temă pentru acasă'),
            ('activitate', 'Activitate în clasă'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Tip evaluare'
    )
    data = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data',
        initial=forms.widgets.SelectDateWidget().value_from_datadict
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            from apps.subjects.models import Subject
            self.fields['subject'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')

        # Setează data de azi ca default
        from datetime import date
        self.fields['data'].initial = date.today()