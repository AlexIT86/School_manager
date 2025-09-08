from django import forms
from django.core.validators import FileExtensionValidator
from django.conf import settings
from .models import Subject, SubjectFile, SubjectNote


class SubjectForm(forms.ModelForm):
    """Form pentru crearea și editarea materiilor"""

    class Meta:
        model = Subject
        fields = ['nume', 'nume_profesor', 'sala', 'culoare', 'descriere', 'manual', 'rating', 'activa']
        labels = {
            'nume': 'Numele materiei',
            'nume_profesor': 'Numele profesorului',
            'sala': 'Sala de clasă',
            'culoare': 'Culoare pentru calendar',
            'descriere': 'Descriere și notițe',
            'manual': 'Manual utilizat',
            'rating': 'Importanță (1-5 stele)',
            'activa': 'Materia este activă',
        }
        widgets = {
            'nume': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Matematică, Română, Istorie',
                'required': True
            }),
            'nume_profesor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Prof. Maria Popescu'
            }),
            'sala': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: A12, B5, Laborator Informatică'
            }),
            'culoare': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'style': 'height: 45px;'
            }),
            'descriere': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notițe despre materie, obiective, observații...'
            }),
            'manual': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Manual de Matematică clasa a 6-a, Editura Humanitas'
            }),
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Culori predefinite populare pentru materii
        self.predefined_colors = [
            ('#FF6B6B', 'Roșu coral'),
            ('#4ECDC4', 'Turcoaz'),
            ('#45B7D1', 'Albastru'),
            ('#96CEB4', 'Verde mentă'),
            ('#FFEAA7', 'Galben'),
            ('#DDA0DD', 'Violet'),
            ('#98D8C8', 'Verde aqua'),
            ('#F7DC6F', 'Galben auriu'),
            ('#BB8FCE', 'Lavandă'),
            ('#85C1E9', 'Albastru deschis'),
        ]

    def clean_nume(self):
        """Validare nume materie"""
        nume = self.cleaned_data['nume']
        if len(nume) < 2:
            raise forms.ValidationError('Numele materiei trebuie să aibă cel puțin 2 caractere.')
        return nume.title()  # Formatare cu prima literă mare


class SubjectFileForm(forms.ModelForm):
    """Form pentru upload-ul fișierelor la materii"""

    class Meta:
        model = SubjectFile
        fields = ['nume', 'fisier', 'descriere']
        labels = {
            'nume': 'Numele fișierului',
            'fisier': 'Selectează fișierul',
            'descriere': 'Descriere (opțional)',
        }
        widgets = {
            'nume': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Notițe capitol 3, Exerciții rezolvate'
            }),
            'fisier': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': ','.join([f'.{ext}' for ext in getattr(settings, 'ALLOWED_FILE_EXTENSIONS', [
                    'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif',
                    'mp3', 'mp4', 'avi', 'mov', 'zip', 'rar', 'ppt', 'pptx'
                ])])
            }),
            'descriere': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Descriere scurtă a fișierului...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Validatori pentru fișier
        allowed_extensions = getattr(settings, 'ALLOWED_FILE_EXTENSIONS', [
            'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif',
            'mp3', 'mp4', 'avi', 'mov', 'zip', 'rar', 'ppt', 'pptx', 'xls', 'xlsx'
        ])

        self.fields['fisier'].validators.append(
            FileExtensionValidator(allowed_extensions=allowed_extensions)
        )

        # Informații despre tipurile de fișiere acceptate
        self.allowed_info = {
            'documents': ['pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx', 'xls', 'xlsx'],
            'images': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
            'media': ['mp3', 'mp4', 'avi', 'mov'],
            'archives': ['zip', 'rar']
        }

    def clean_fisier(self):
        """Validare mărime fișier"""
        fisier = self.cleaned_data['fisier']
        if fisier:
            # Verifică mărimea (default 10MB)
            max_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 10 * 1024 * 1024)
            if fisier.size > max_size:
                max_size_mb = max_size / (1024 * 1024)
                raise forms.ValidationError(
                    f'Fișierul este prea mare. Mărimea maximă permisă este {max_size_mb:.1f}MB.')
        return fisier

    def clean_nume(self):
        """Auto-completare nume dacă nu este specificat"""
        nume = self.cleaned_data.get('nume')
        fisier = self.cleaned_data.get('fisier')

        if not nume and fisier:
            # Folosește numele fișierului original (fără extensie)
            nume = fisier.name.rsplit('.', 1)[0]

        return nume


class SubjectNoteForm(forms.ModelForm):
    """Form pentru crearea și editarea notițelor"""

    class Meta:
        model = SubjectNote
        fields = ['titlu', 'continut', 'important', 'tags']
        labels = {
            'titlu': 'Titlul notiței',
            'continut': 'Conținutul notiței',
            'important': 'Notița este importantă',
            'tags': 'Tag-uri (separate prin virgulă)',
        }
        widgets = {
            'titlu': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: Formule importante, Rezumat capitol 5',
                'required': True
            }),
            'continut': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Scrie aici conținutul notiței...',
                'required': True
            }),
            'important': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ex: formule, rezumat, important, examen',
                'data-toggle': 'tooltip',
                'title': 'Folosește virgula pentru a separa tag-urile'
            }),
        }

    def clean_tags(self):
        """Formatare tags"""
        tags = self.cleaned_data.get('tags', '')
        if tags:
            # Curăță și formatează tag-urile
            tag_list = [tag.strip().lower() for tag in tags.split(',') if tag.strip()]
            # Elimină duplicatele păstrând ordinea
            seen = set()
            unique_tags = []
            for tag in tag_list:
                if tag not in seen:
                    seen.add(tag)
                    unique_tags.append(tag)
            return ', '.join(unique_tags)
        return tags


class SubjectSearchForm(forms.Form):
    """Form pentru căutarea în materii"""
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Caută în materii, profesori, sale...',
            'type': 'search'
        }),
        label='Căutare'
    )

    active_only = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Doar materiile active'
    )

    sort_by = forms.ChoiceField(
        choices=[
            ('nume', 'Nume A-Z'),
            ('-nume', 'Nume Z-A'),
            ('nume_profesor', 'Profesor A-Z'),
            ('-created_at', 'Cel mai recent'),
            ('created_at', 'Cel mai vechi'),
        ],
        required=False,
        initial='nume',
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Sortare'
    )


class BulkSubjectActionForm(forms.Form):
    """Form pentru acțiuni în masă asupra materiilor"""
    action = forms.ChoiceField(
        choices=[
            ('activate', 'Activează materiile selectate'),
            ('deactivate', 'Dezactivează materiile selectate'),
            ('delete', 'Șterge materiile selectate'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Acțiune'
    )

    selected_subjects = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )

    def clean_selected_subjects(self):
        """Validare și parsare ID-uri materii selectate"""
        subjects_str = self.cleaned_data['selected_subjects']
        try:
            subject_ids = [int(id) for id in subjects_str.split(',') if id.strip()]
            if not subject_ids:
                raise forms.ValidationError('Nu ai selectat nicio materie.')
            return subject_ids
        except ValueError:
            raise forms.ValidationError('ID-uri invalide pentru materii.')


class SubjectImportForm(forms.Form):
    """Form pentru importul materiilor dintr-un fișier CSV/Excel"""
    file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'xlsx', 'xls'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        }),
        label='Fișier import',
        help_text='Acceptă fișiere CSV sau Excel (.xlsx, .xls)'
    )

    overwrite_existing = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Suprascrie materiile existente',
        help_text='Dacă o materie cu același nume există deja, o va actualiza'
    )