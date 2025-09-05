from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from datetime import date
from .models import Grade, Semester, GradeGoal
from apps.subjects.models import Subject


class GradeForm(forms.ModelForm):
    """Form pentru adăugarea și editarea notelor/absențelor"""

    class Meta:
        model = Grade
        fields = [
            'subject', 'tip', 'valoare', 'tip_evaluare', 'descriere',
            'data', 'semestru', 'motivata', 'data_motivare',
            'note_personale', 'importante'
        ]
        labels = {
            'subject': 'Materia',
            'tip': 'Tipul',
            'valoare': 'Nota (1.00 - 10.00)',
            'tip_evaluare': 'Tipul evaluării',
            'descriere': 'Descrierea evaluării',
            'data': 'Data',
            'semestru': 'Semestrul',
            'motivata': 'Absența este motivată',
            'data_motivare': 'Data motivării',
            'note_personale': 'Notițe personale',
            'importante': 'Notă importantă (teză, test important)',
        }
        widgets = {
            'subject': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'tip': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'valoare': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.25',
                'min': '1.00',
                'max': '10.00'
            }),
            'tip_evaluare': forms.Select(attrs={
                'class': 'form-control'
            }),
            'descriere': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Capitolul 3, Ecuații de gradul 2'
            }),
            'data': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'semestru': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '2'
            }),
            'motivata': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'data_motivare': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'note_personale': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notițe personale despre această evaluare...'
            }),
            'importante': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
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
        if not self.instance.pk:
            self.fields['data'].initial = date.today()
            # Determină semestrul curent
            current_month = date.today().month
            current_semester = 1 if current_month >= 9 or current_month <= 1 else 2
            self.fields['semestru'].initial = current_semester

        # Organizează câmpurile în grupuri
        self.field_groups = [
            {
                'title': 'Informații de bază',
                'fields': ['subject', 'tip', 'data', 'semestru'],
                'icon': 'fas fa-info-circle'
            },
            {
                'title': 'Detalii notă',
                'fields': ['valoare', 'tip_evaluare', 'descriere', 'importante'],
                'icon': 'fas fa-star',
                'show_condition': 'nota'
            },
            {
                'title': 'Detalii absență',
                'fields': ['motivata', 'data_motivare'],
                'icon': 'fas fa-calendar-times',
                'show_condition': 'absenta,absenta_motivata'
            },
            {
                'title': 'Note personale',
                'fields': ['note_personale'],
                'icon': 'fas fa-sticky-note'
            }
        ]

    def clean(self):
        """Validări custom"""
        cleaned_data = super().clean()
        tip = cleaned_data.get('tip')
        valoare = cleaned_data.get('valoare')
        motivata = cleaned_data.get('motivata')
        data_motivare = cleaned_data.get('data_motivare')

        # Validare: notele trebuie să aibă valoare
        if tip == 'nota' and not valoare:
            raise forms.ValidationError('Notele trebuie să aibă o valoare.')

        # Validare: absențele nu pot avea valoare
        if tip in ['absenta', 'absenta_motivata'] and valoare:
            raise forms.ValidationError('Absențele nu pot avea valoare numerică.')

        # Validare: data motivării pentru absențe motivate
        if motivata and not data_motivare:
            cleaned_data['data_motivare'] = date.today()

        # Auto-setare tip pentru absențe motivate
        if tip == 'absenta' and motivata:
            cleaned_data['tip'] = 'absenta_motivata'

        return cleaned_data


class SemesterForm(forms.ModelForm):
    """Form pentru gestionarea semestrelor"""

    class Meta:
        model = Semester
        fields = ['numar', 'an_scolar', 'data_inceput', 'data_sfarsit', 'activ']
        labels = {
            'numar': 'Numărul semestrului',
            'an_scolar': 'Anul școlar',
            'data_inceput': 'Data de început',
            'data_sfarsit': 'Data de sfârșit',
            'activ': 'Semestru activ',
        }
        widgets = {
            'numar': forms.Select(
                choices=[(1, 'Semestrul 1'), (2, 'Semestrul 2')],
                attrs={'class': 'form-control', 'required': True}
            ),
            'an_scolar': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: 2024-2025',
                'required': True
            }),
            'data_inceput': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'data_sfarsit': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'activ': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Setează valori default pentru semestru nou
        if not self.instance.pk:
            current_year = date.today().year
            current_month = date.today().month

            if current_month >= 9:  # An școlar nou începe în septembrie
                self.fields['an_scolar'].initial = f"{current_year}-{current_year + 1}"
                self.fields['numar'].initial = 1
                self.fields['data_inceput'].initial = date(current_year, 9, 15)
                self.fields['data_sfarsit'].initial = date(current_year + 1, 1, 31)
            elif current_month <= 1:  # Încă în primul semestru
                self.fields['an_scolar'].initial = f"{current_year - 1}-{current_year}"
                self.fields['numar'].initial = 1
            else:  # Al doilea semestru
                self.fields['an_scolar'].initial = f"{current_year - 1}-{current_year}"
                self.fields['numar'].initial = 2
                self.fields['data_inceput'].initial = date(current_year, 2, 1)
                self.fields['data_sfarsit'].initial = date(current_year, 6, 15)

    def clean(self):
        """Validări custom pentru semestru"""
        cleaned_data = super().clean()
        data_inceput = cleaned_data.get('data_inceput')
        data_sfarsit = cleaned_data.get('data_sfarsit')

        if data_inceput and data_sfarsit:
            if data_sfarsit <= data_inceput:
                raise forms.ValidationError('Data de sfârșit trebuie să fie după data de început.')

        return cleaned_data


class GradeGoalForm(forms.ModelForm):
    """Form pentru obiectivele de note"""

    class Meta:
        model = GradeGoal
        fields = ['subject', 'semester', 'media_dorita', 'descriere']
        labels = {
            'subject': 'Materia',
            'semester': 'Semestrul',
            'media_dorita': 'Media dorită',
            'descriere': 'De ce această medie este importantă',
        }
        widgets = {
            'subject': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'semester': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'media_dorita': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.25',
                'min': '1.00',
                'max': '10.00',
                'required': True
            }),
            'descriere': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ex: Vreau să îmbunătățesc media pentru a intra la liceul dorit...'
            }),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            # Filtrează materiile și semestrele pentru utilizatorul curent
            self.fields['subject'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')

            self.fields['semester'].queryset = Semester.objects.filter(
                user=user
            ).order_by('-an_scolar', '-numar')

            # Setează semestrul activ ca default
            active_semester = Semester.objects.filter(user=user, activ=True).first()
            if active_semester and not self.instance.pk:
                self.fields['semester'].initial = active_semester


class GradeFilterForm(forms.Form):
    """Form pentru filtrarea notelor și absențelor"""

    GRADE_TYPE_CHOICES = [
        ('', 'Toate'),
        ('nota', 'Note'),
        ('absenta', 'Absențe nemotivate'),
        ('absenta_motivata', 'Absențe motivate'),
        ('intarziere', 'Întârzieri'),
    ]

    DATE_RANGE_CHOICES = [
        ('', 'Oricând'),
        ('this_week', 'Săptămâna aceasta'),
        ('this_month', 'Luna aceasta'),
        ('last_month', 'Luna trecută'),
    ]

    subject = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label='Toate materiile',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Materia'
    )

    grade_type = forms.ChoiceField(
        choices=GRADE_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Tipul'
    )

    semester = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Semestrul'
    )

    date_range = forms.ChoiceField(
        choices=DATE_RANGE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Perioada'
    )

    min_grade = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.25',
            'min': '1.00',
            'max': '10.00',
            'placeholder': '1.00'
        }),
        label='Nota minimă'
    )

    max_grade = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.25',
            'min': '1.00',
            'max': '10.00',
            'placeholder': '10.00'
        }),
        label='Nota maximă'
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            # Filtrează materiile
            self.fields['subject'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')

            # Populează opțiunile pentru semestru
            semester_choices = [('', 'Toate semestrele')]
            semester_choices.extend([(1, 'Semestrul 1'), (2, 'Semestrul 2')])
            self.fields['semester'].choices = semester_choices


class QuickGradeForm(forms.Form):
    """Form rapid pentru adăugarea notelor din dashboard"""

    subject = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        label='Materia'
    )

    grade_value = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(1.0), MaxValueValidator(10.0)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm',
            'step': '0.25',
            'min': '1.00',
            'max': '10.00'
        }),
        label='Nota'
    )

    grade_type = forms.ChoiceField(
        choices=[
            ('oral', 'Oral'),
            ('test', 'Test'),
            ('teza', 'Teză'),
            ('proiect', 'Proiect'),
        ],
        initial='test',
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        label='Tip'
    )

    description = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Descriere (opțional)'
        }),
        label='Descriere'
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')


class BulkGradeActionForm(forms.Form):
    """Form pentru acțiuni în masă asupra notelor"""

    ACTION_CHOICES = [
        ('delete', 'Șterge notele/absențele selectate'),
        ('change_semester', 'Schimbă semestrul'),
        ('mark_important', 'Marchează ca importante'),
        ('unmark_important', 'Elimină marcajul important'),
        ('excuse_absences', 'Motivează absențele selectate'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Acțiune'
    )

    selected_grades = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    # Câmpuri condiționale
    new_semester = forms.ChoiceField(
        choices=[(1, 'Semestrul 1'), (2, 'Semestrul 2')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Noul semestru'
    )

    def clean_selected_grades(self):
        """Validare și parsare ID-uri note selectate"""
        grades_str = self.cleaned_data['selected_grades']
        try:
            grade_ids = [int(id) for id in grades_str.split(',') if id.strip()]
            if not grade_ids:
                raise forms.ValidationError('Nu ai selectat nicio notă/absență.')
            return grade_ids
        except ValueError:
            raise forms.ValidationError('ID-uri invalide pentru note.')

    def clean(self):
        """Validare cross-field"""
        cleaned_data = super().clean()
        action = cleaned_data.get('action')

        if action == 'change_semester' and not cleaned_data.get('new_semester'):
            raise forms.ValidationError('Trebuie să selectezi noul semestru.')

        return cleaned_data


class GradeImportForm(forms.Form):
    """Form pentru importul notelor din fișier"""

    file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'xlsx', 'xls'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        }),
        label='Fișier import',
        help_text='Format acceptat: CSV sau Excel cu coloane: Materie, Tip, Valoare, Data, Semestru, Descriere'
    )

    overwrite_existing = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Suprascrie notele existente',
        help_text='Dacă o notă cu aceeași dată și materie există, o va actualiza'
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


class GradeExportForm(forms.Form):
    """Form pentru exportul notelor"""

    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('xlsx', 'Excel (XLSX)'),
        ('pdf', 'PDF - Catalog'),
    ]

    CONTENT_CHOICES = [
        ('all', 'Toate notele și absențele'),
        ('grades_only', 'Doar notele'),
        ('absences_only', 'Doar absențele'),
        ('by_subject', 'Grupate pe materii'),
    ]

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial='xlsx',
        widget=forms.RadioSelect(),
        label='Format export'
    )

    content = forms.ChoiceField(
        choices=CONTENT_CHOICES,
        initial='all',
        widget=forms.RadioSelect(),
        label='Conținut export'
    )

    include_statistics = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Include statistici',
        help_text='Include medii, numărul de note, absențe per materie'
    )

    semester_filter = forms.ChoiceField(
        choices=[
            ('all', 'Toate semestrele'),
            ('1', 'Doar semestrul 1'),
            ('2', 'Doar semestrul 2'),
        ],
        initial='all',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Filtrare semestru'
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='De la data (opțional)'
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Până la data (opțional)'
    )

    def clean(self):
        """Validare pentru export"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')

        if date_from and date_to and date_to < date_from:
            raise forms.ValidationError('Data de sfârșit trebuie să fie după data de început.')

        return cleaned_data


class AbsenceExcuseForm(forms.Form):
    """Form pentru motivarea absențelor"""

    excuse_reason = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Motivul absenței (opțional)'
        }),
        label='Motivul absenței'
    )

    excuse_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data motivării',
        initial=date.today
    )

    add_note = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Notă personală despre motivare (opțional)'
        }),
        label='Notă personală'
    )


class GradeAnalysisForm(forms.Form):
    """Form pentru analiza performanței"""

    ANALYSIS_TYPE_CHOICES = [
        ('trend', 'Tendința notelor în timp'),
        ('subject_comparison', 'Comparație între materii'),
        ('semester_comparison', 'Comparație între semestre'),
        ('grade_distribution', 'Distribuția notelor'),
        ('absence_pattern', 'Paternul absențelor'),
    ]

    TIME_PERIOD_CHOICES = [
        ('last_month', 'Ultima lună'),
        ('last_3_months', 'Ultimele 3 luni'),
        ('last_6_months', 'Ultimele 6 luni'),
        ('this_year', 'Anul acesta'),
        ('all_time', 'Tot timpul'),
    ]

    analysis_type = forms.ChoiceField(
        choices=ANALYSIS_TYPE_CHOICES,
        initial='trend',
        widget=forms.RadioSelect(),
        label='Tipul analizei'
    )

    time_period = forms.ChoiceField(
        choices=TIME_PERIOD_CHOICES,
        initial='last_3_months',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Perioada de timp'
    )

    selected_subjects = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label='Materii selectate (opțional)'
    )

    include_absences = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Include absențele în analiză'
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['selected_subjects'].queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')


class StudyPlanForm(forms.Form):
    """Form pentru planul de studiu bazat pe note"""

    PRIORITY_CHOICES = [
        ('grades', 'Prioritizează materiile cu note mici'),
        ('absences', 'Prioritizează materiile cu multe absențe'),
        ('goals', 'Prioritizează obiectivele neîndeplinite'),
        ('balanced', 'Abordare echilibrată'),
    ]

    INTENSITY_CHOICES = [
        ('light', 'Ușor (1-2 ore pe zi)'),
        ('moderate', 'Moderat (2-4 ore pe zi)'),
        ('intensive', 'Intensiv (4+ ore pe zi)'),
    ]

    priority_strategy = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        initial='balanced',
        widget=forms.RadioSelect(),
        label='Strategia de prioritizare'
    )

    study_intensity = forms.ChoiceField(
        choices=INTENSITY_CHOICES,
        initial='moderate',
        widget=forms.RadioSelect(),
        label='Intensitatea studiului'
    )

    focus_subjects = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label='Materii de focalizat (opțional)'
    )

    target_improvement = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        initial=1.0,
        validators=[MinValueValidator(0.25), MaxValueValidator(3.0)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.25',
            'min': '0.25',
            'max': '3.00'
        }),
        label='Îmbunătățirea dorită (puncte)',
        help_text='Cu câte puncte vrei să îmbunătățești media'
    )

    study_days_per_week = forms.IntegerField(
        min_value=1,
        max_value=7,
        initial=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '7'
        }),
        label='Zile de studiu pe săptămână'
    )

    exclude_subjects = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label='Exclude materii (opțional)',
        help_text='Materii care nu necesită studiu suplimentar'
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            subject_queryset = Subject.objects.filter(
                user=user,
                activa=True
            ).order_by('nume')

            self.fields['focus_subjects'].queryset = subject_queryset
            self.fields['exclude_subjects'].queryset = subject_queryset