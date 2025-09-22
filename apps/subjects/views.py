from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.db.models import Count, Avg
from django.core.paginator import Paginator
from django.conf import settings
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
import re
import os

from .models import Subject, SubjectFile, SubjectNote
from django.utils.text import get_valid_filename
from .forms import SubjectForm, SubjectFileForm, SubjectNoteForm
from apps.homework.models import Homework
from apps.grades.models import Grade


@login_required
def subject_list_view(request):
    """Lista tuturor materiilor"""
    subjects = Subject.objects.filter(user=request.user).order_by('nume')

    # Statistici pentru fiecare materie
    subjects_with_stats = []
    for subject in subjects:
        stats = {
            'total_homework': subject.homework_set.filter(finalizata=False).count(),
            'total_files': subject.files.count(),
            'total_notes': subject.notes.count(),
            'avg_grade': subject.grade_set.filter(tip='nota').aggregate(
                avg=Avg('valoare')
            )['avg'],
            'total_absences': subject.grade_set.filter(
                tip__in=['absenta', 'absenta_motivata']
            ).count(),
        }
        subjects_with_stats.append({
            'subject': subject,
            'stats': stats
        })

    # Quick stats
    active_count = subjects.filter(activa=True).count()
    with_homework_count = subjects.filter(homework_set__finalizata=False).distinct().count()

    context = {
        'subjects_with_stats': subjects_with_stats,
        'quick_stats': {
            'active_count': active_count,
            'with_homework_count': with_homework_count,
        }
    }

    return render(request, 'subjects/subject_list.html', context)


@login_required
def subject_detail_view(request, subject_id):
    """Detalii despre o materie specifică"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)

    # Teme active
    active_homework = subject.homework_set.filter(finalizata=False).order_by('deadline')

    # Teme finalizate recent
    completed_homework = subject.homework_set.filter(finalizata=True).order_by('-data_finalizare')[:5]

    # Note recente
    recent_grades = subject.grade_set.filter(tip='nota').order_by('-data')[:10]

    # Absențe
    absences = subject.grade_set.filter(
        tip__in=['absenta', 'absenta_motivata']
    ).order_by('-data')[:10]

    # Fișiere
    files = subject.files.order_by('-uploaded_at')

    # Notițe
    notes = subject.notes.order_by('-updated_at')

    # Formulare pentru adăugare rapidă
    file_form = SubjectFileForm()
    note_form = SubjectNoteForm()

    # Statistici
    stats = {
        'media_note': subject.media_note,
        'total_note': recent_grades.count(),
        'numar_absente': subject.numar_absente,
        'ore_pe_saptamana': subject.ore_pe_saptamana,
        'teme_active': active_homework.count(),
        'total_fisiere': files.count(),
        'total_notite': notes.count(),
    }

    context = {
        'subject': subject,
        'active_homework': active_homework,
        'completed_homework': completed_homework,
        'recent_grades': recent_grades,
        'absences': absences,
        'files': files,
        'notes': notes,
        'file_form': file_form,
        'note_form': note_form,
        'stats': stats,
    }

    return render(request, 'subjects/subject_detail.html', context)


@login_required
def subject_create_view(request):
    """Creare materie nouă"""
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.user = request.user
            subject.save()
            messages.success(request, f'Materia "{subject.nume}" a fost adăugată cu succes!')
            return redirect('subjects:detail', subject_id=subject.id)
    else:
        form = SubjectForm()

    context = {
        'form': form,
        'title': 'Adaugă materie nouă',
    }

    return render(request, 'subjects/subject_form.html', context)


@login_required
def subject_edit_view(request, subject_id):
    """Editare materie existentă"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)

    # Doar superadmin poate edita toate câmpurile din materie
    if not request.user.is_superuser:
        raise PermissionDenied

    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, f'Materia "{subject.nume}" a fost actualizată!')
            return redirect('subjects:detail', subject_id=subject.id)
    else:
        # Permite setarea rapidă a rating-ului din query (?rating=1..5)
        rating = request.GET.get('rating')
        if rating and rating.isdigit():
            r = int(rating)
            if 1 <= r <= 5:
                subject.rating = r
                subject.save(update_fields=['rating'])
                messages.success(request, f'Rating setat la {r} stele pentru "{subject.nume}"!')
                return redirect('subjects:list')
        form = SubjectForm(instance=subject)

    context = {
        'form': form,
        'subject': subject,
        'title': f'Editează materia {subject.nume}',
    }

    return render(request, 'subjects/subject_form.html', context)


@login_required
def subject_set_rating_view(request, subject_id, value):
    """Setează rating-ul unei materii (AJAX sau GET fallback)."""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    try:
        value = int(value)
        if value < 1 or value > 5:
            raise ValueError
        subject.rating = value
        subject.save(update_fields=['rating'])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'rating': subject.rating})
        messages.success(request, f'Rating actualizat la {value} stele pentru "{subject.nume}"!')
    except Exception:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Rating invalid'}, status=400)
        messages.error(request, 'Rating invalid.')
    return redirect('subjects:list')


@login_required
@require_POST
def subject_set_color_view(request, subject_id):
    """Setează culoarea unei materii (hex #RRGGBB). Doar pentru proprietar."""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    color = (request.POST.get('color') or '').strip()
    if not color:
        return JsonResponse({'success': False, 'error': 'Culoare lipsă'}, status=400)
    if not re.match(r'^#[0-9a-fA-F]{6}$', color):
        return JsonResponse({'success': False, 'error': 'Format culoare invalid (ex: #1A2B3C)'}, status=400)
    subject.culoare = color
    subject.save(update_fields=['culoare'])
    return JsonResponse({'success': True, 'color': subject.culoare})


@login_required
def subject_delete_view(request, subject_id):
    """Ștergere materie"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)

    # Doar superadmin poate șterge materia
    if not request.user.is_superuser:
        raise PermissionDenied

    if request.method == 'POST':
        subject_name = subject.nume
        subject.delete()
        messages.success(request, f'Materia "{subject_name}" a fost ștearsă!')
        return redirect('subjects:list')

    # Verifică dependențele
    dependencies = {
        'homework_count': subject.homework_set.count(),
        'grades_count': subject.grade_set.count(),
        'files_count': subject.files.count(),
        'notes_count': subject.notes.count(),
        'schedule_count': subject.schedule_entries.count(),
    }

    context = {
        'subject': subject,
        'dependencies': dependencies,
    }

    return render(request, 'subjects/subject_delete.html', context)


@login_required
def subject_file_upload_view(request, subject_id):
    """Upload fișier pentru o materie"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)

    if request.method == 'POST':
        form = SubjectFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_obj = form.save(commit=False)
            file_obj.subject = subject
            file_obj.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Răspuns AJAX
                return JsonResponse({
                    'success': True,
                    'file_id': file_obj.id,
                    'file_name': file_obj.nume,
                    'file_url': file_obj.fisier.url,
                    'file_size': file_obj.marime_formatata,
                    'file_type': file_obj.get_tip_display()
                })
            else:
                messages.success(request, f'Fișierul "{file_obj.nume}" a fost încărcat cu succes!')
                return redirect('subjects:detail', subject_id=subject.id)
    else:
        form = SubjectFileForm()

    context = {
        'form': form,
        'subject': subject,
    }

    return render(request, 'subjects/file_upload.html', context)


@login_required
def subject_file_delete_view(request, subject_id, file_id):
    """Ștergere fișier"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    file_obj = get_object_or_404(SubjectFile, id=file_id, subject=subject)

    if request.method == 'POST':
        file_name = file_obj.nume
        # Șterge fișierul din storage backend
        if file_obj.fisier:
            try:
                file_obj.fisier.delete(save=False)
            except Exception:
                pass

        file_obj.delete()
        messages.success(request, f'Fișierul "{file_name}" a fost șters!')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

    return redirect('subjects:detail', subject_id=subject.id)


@login_required
def subject_note_create_view(request, subject_id):
    """Creare notiță pentru o materie"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)

    if request.method == 'POST':
        form = SubjectNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.subject = subject
            note.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'note_id': note.id,
                    'note_title': note.titlu,
                    'note_content': note.continut[:100] + ('...' if len(note.continut) > 100 else ''),
                    'note_date': note.created_at.strftime('%d.%m.%Y %H:%M')
                })
            else:
                messages.success(request, f'Notița "{note.titlu}" a fost adăugată!')
                return redirect('subjects:detail', subject_id=subject.id)
    else:
        form = SubjectNoteForm()

    context = {
        'form': form,
        'subject': subject,
    }

    return render(request, 'subjects/note_form.html', context)


@login_required
def subject_note_edit_view(request, subject_id, note_id):
    """Editare notiță"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    note = get_object_or_404(SubjectNote, id=note_id, subject=subject)

    if request.method == 'POST':
        form = SubjectNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, f'Notița "{note.titlu}" a fost actualizată!')
            return redirect('subjects:detail', subject_id=subject.id)
    else:
        form = SubjectNoteForm(instance=note)

    context = {
        'form': form,
        'subject': subject,
        'note': note,
    }

    return render(request, 'subjects/note_form.html', context)


@login_required
def subject_note_delete_view(request, subject_id, note_id):
    """Ștergere notiță"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    note = get_object_or_404(SubjectNote, id=note_id, subject=subject)

    if request.method == 'POST':
        note_title = note.titlu
        note.delete()
        messages.success(request, f'Notița "{note_title}" a fost ștearsă!')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

    return redirect('subjects:detail', subject_id=subject.id)


@login_required
def subject_files_view(request, subject_id):
    """Vizualizare toate fișierele unei materii"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)

    # Filtrare după tip
    file_type = request.GET.get('type', '')
    files = subject.files.all()

    if file_type:
        files = files.filter(tip=file_type)

    # Paginare
    paginator = Paginator(files.order_by('-uploaded_at'), 12)  # 12 fișiere per pagină
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Tipuri disponibile pentru filtrare
    available_types = subject.files.values_list('tip', flat=True).distinct()

    context = {
        'subject': subject,
        'page_obj': page_obj,
        'current_type': file_type,
        'available_types': available_types,
        'file_types': SubjectFile.FILE_TYPES,
    }

    return render(request, 'subjects/subject_files.html', context)


@login_required
def subject_notes_view(request, subject_id):
    """Vizualizare toate notițele unei materii"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)

    # Filtrare după tag
    tag = request.GET.get('tag', '')
    notes = subject.notes.all()

    if tag:
        notes = notes.filter(tags__icontains=tag)

    # Căutare
    search = request.GET.get('search', '')
    if search:
        notes = notes.filter(
            models.Q(titlu__icontains=search) |
            models.Q(continut__icontains=search)
        )

    # Paginare
    paginator = Paginator(notes.order_by('-updated_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Tag-uri disponibile
    all_tags = []
    for note in subject.notes.all():
        all_tags.extend(note.tag_list)
    available_tags = list(set(all_tags))

    context = {
        'subject': subject,
        'page_obj': page_obj,
        'current_tag': tag,
        'current_search': search,
        'available_tags': available_tags,
    }

    return render(request, 'subjects/subject_notes.html', context)


@login_required
def subject_stats_view(request, subject_id):
    """Statistici detaliate pentru o materie"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)

    # Note și statistici
    grades = subject.grade_set.filter(tip='nota').order_by('data')
    grade_stats = {
        'total': grades.count(),
        'media': grades.aggregate(avg=Avg('valoare'))['avg'],
        'maxima': grades.aggregate(max=models.Max('valoare'))['max'],
        'minima': grades.aggregate(min=models.Min('valoare'))['min'],
    }

    # Distribuția notelor
    grade_distribution = {}
    for i in range(1, 11):
        count = grades.filter(valoare__gte=i, valoare__lt=i + 1).count()
        grade_distribution[i] = count

    # Progresul în timp (ultimele 10 note)
    recent_grades = list(grades.values('valoare', 'data')[-10:])

    # Absențe
    absences = subject.grade_set.filter(tip__in=['absenta', 'absenta_motivata'])
    absence_stats = {
        'total': absences.count(),
        'motivate': absences.filter(tip='absenta_motivata').count(),
        'nemotivate': absences.filter(tip='absenta').count(),
    }

    # Teme
    homework_stats = {
        'total': subject.homework_set.count(),
        'finalizate': subject.homework_set.filter(finalizata=True).count(),
        'active': subject.homework_set.filter(finalizata=False).count(),
        'intarziate': subject.homework_set.filter(
            finalizata=False,
            deadline__lt=timezone.now().date()
        ).count(),
    }

    context = {
        'subject': subject,
        'grade_stats': grade_stats,
        'grade_distribution': grade_distribution,
        'recent_grades': recent_grades,
        'absence_stats': absence_stats,
        'homework_stats': homework_stats,
    }

    return render(request, 'subjects/subject_stats.html', context)


@login_required
def download_subject_file(request, subject_id, file_id):
    """Download fișier"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)
    file_obj = get_object_or_404(SubjectFile, id=file_id, subject=subject)

    if file_obj.fisier:
        try:
            # Deschide fișierul din storage (compatibil cu orice backend)
            file_obj.fisier.open('rb')
            safe_name = get_valid_filename(file_obj.nume or os.path.basename(file_obj.fisier.name))
            return FileResponse(file_obj.fisier, as_attachment=True, filename=safe_name)
        except Exception:
            pass

    messages.error(request, 'Fișierul nu a fost găsit!')
    return redirect('subjects:detail', subject_id=subject.id)