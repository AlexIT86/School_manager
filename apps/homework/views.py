from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Avg, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import date, timedelta
import calendar
import json
from django.core.serializers.json import DjangoJSONEncoder
import os

from .models import Homework, HomeworkFile, HomeworkSession, HomeworkReminder
from .forms import HomeworkForm, HomeworkFileForm, HomeworkSessionForm, HomeworkFilterForm
from apps.subjects.models import Subject
from apps.core.models import Notification
from django.conf import settings

try:
    from apps.core.email_utils import send_email
except Exception:
    send_email = None


@login_required
def homework_list_view(request):
    """Lista tuturor temelor cu filtrare și sortare"""
    user = request.user

    # Form pentru filtrare
    filter_form = HomeworkFilterForm(user=user, data=request.GET)

    # Queryset de bază
    homework_list = Homework.objects.filter(user=user)

    # Aplicare filtre din form
    if filter_form.is_valid():
        subject = filter_form.cleaned_data.get('subject')
        status = filter_form.cleaned_data.get('status')
        priority = filter_form.cleaned_data.get('priority')
        deadline_range = filter_form.cleaned_data.get('deadline_range')
        search = filter_form.cleaned_data.get('search')

        if subject:
            homework_list = homework_list.filter(subject=subject)

        if status == 'active':
            homework_list = homework_list.filter(finalizata=False)
        elif status == 'completed':
            homework_list = homework_list.filter(finalizata=True)
        elif status == 'overdue':
            homework_list = homework_list.filter(finalizata=False, deadline__lt=date.today())

        if priority:
            homework_list = homework_list.filter(prioritate=priority)

        if deadline_range == 'today':
            homework_list = homework_list.filter(deadline=date.today())
        elif deadline_range == 'tomorrow':
            homework_list = homework_list.filter(deadline=date.today() + timedelta(days=1))
        elif deadline_range == 'this_week':
            start_week = date.today()
            end_week = start_week + timedelta(days=7)
            homework_list = homework_list.filter(deadline__range=[start_week, end_week])
        elif deadline_range == 'next_week':
            start_week = date.today() + timedelta(days=7)
            end_week = start_week + timedelta(days=7)
            homework_list = homework_list.filter(deadline__range=[start_week, end_week])

        if search:
            homework_list = homework_list.filter(
                Q(titlu__icontains=search) |
                Q(descriere__icontains=search) |
                Q(subject__nume__icontains=search)
            )

    # Sortare
    sort_by = request.GET.get('sort', 'deadline')
    if sort_by == 'deadline':
        homework_list = homework_list.order_by('deadline', '-prioritate')
    elif sort_by == 'priority':
        homework_list = homework_list.order_by('-prioritate', 'deadline')
    elif sort_by == 'subject':
        homework_list = homework_list.order_by('subject__nume', 'deadline')
    elif sort_by == 'progress':
        homework_list = homework_list.order_by('-progres', 'deadline')
    else:
        homework_list = homework_list.order_by('deadline')

    # Paginare
    paginator = Paginator(homework_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistici pentru dashboard
    stats = {
        'total': homework_list.count(),
        'active': homework_list.filter(finalizata=False).count(),
        'completed_today': homework_list.filter(finalizata=True, data_finalizare__date=date.today()).count(),
        'overdue': homework_list.filter(finalizata=False, deadline__lt=date.today()).count(),
        'due_today': homework_list.filter(finalizata=False, deadline=date.today()).count(),
        'due_tomorrow': homework_list.filter(finalizata=False, deadline=date.today() + timedelta(days=1)).count(),
    }

    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'stats': stats,
        'current_sort': sort_by,
    }

    return render(request, 'homework/homework_list.html', context)


@login_required
def homework_detail_view(request, homework_id):
    """Detalii despre o temă specifică"""
    homework = get_object_or_404(Homework, id=homework_id, user=request.user)

    # Fișiere atașate
    files = homework.files.order_by('-uploaded_at')

    # Sesiuni de lucru
    sessions = homework.sessions.order_by('-inceput')

    # Reminder-uri
    reminders = homework.reminders.order_by('data_reminder')

    # Calculează timpul total lucrat
    total_time_worked = sessions.aggregate(total=Sum('durata_minute'))['total'] or 0

    # Progres și estimări
    progress_info = {
        'progress_percent': homework.progres,
        'estimated_remaining': homework.timp_ramas_estimat,
        'time_worked': total_time_worked,
        'efficiency': (homework.progres / max(total_time_worked, 1)) if total_time_worked > 0 else 0,
    }

    # Verifică dacă există o sesiune activă
    active_session = sessions.filter(sfarsit__isnull=True).first()

    context = {
        'homework': homework,
        'files': files,
        'sessions': sessions,
        'reminders': reminders,
        'progress_info': progress_info,
        'active_session': active_session,
    }

    return render(request, 'homework/homework_detail.html', context)


@login_required
def homework_create_view(request):
    """Creare temă nouă"""
    if request.method == 'POST':
        form = HomeworkForm(user=request.user, data=request.POST)
        if form.is_valid():
            homework = form.save(commit=False)
            homework.user = request.user
            homework.save()

            # Creează reminder automat dacă este activat
            if homework.reminder_activ:
                reminder_date = homework.deadline - timedelta(days=homework.zile_reminder)
                if reminder_date >= date.today():
                    HomeworkReminder.objects.create(
                        homework=homework,
                        data_reminder=reminder_date
                    )

            # Upload inițial imagini (dacă au fost atașate în form)
            try:
                files = request.FILES.getlist('initial_images')
                for idx, file in enumerate(files, start=1):
                    fname = f"{homework.titlu}"[:40].strip() or file.name.rsplit('.', 1)[0]
                    if len(files) > 1:
                        fname = f"{fname}_{idx}"
                    HomeworkFile.objects.create(
                        homework=homework,
                        nume=fname,
                        fisier=file,
                        tip='imagine',
                        descriere='Poză atașată la creare'
                    )
            except Exception:
                pass

            messages.success(request, f'Tema "{homework.titlu}" a fost adăugată cu succes!')

            # Email părinte pentru teme noi (dacă e activat în profil)
            try:
                profile = request.user.student_profile
                parent_email = getattr(profile, 'email_parinte', '')
                if send_email and profile.reminder_teme and parent_email:
                    send_email(
                        to_emails=[parent_email],
                        subject=f'Temă nouă la {homework.subject.nume}',
                        html_content=f"""
                        <p>Bună,</p>
                        <p>A fost adăugată o temă nouă:</p>
                        <ul>
                          <li>Materie: {homework.subject.nume}</li>
                          <li>Titlu: {homework.titlu}</li>
                          <li>Termen: {homework.deadline}</li>
                          <li>Prioritate: {homework.get_prioritate_display() if hasattr(homework, 'get_prioritate_display') else '-'}</li>
                        </ul>
                        """
                    )
            except Exception:
                pass
            return redirect('homework:detail', homework_id=homework.id)
    else:
        form = HomeworkForm(user=request.user)

        # Pre-populează cu materia din URL dacă există
        subject_id = request.GET.get('subject')
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id, user=request.user)
                form.initial['subject'] = subject
            except Subject.DoesNotExist:
                pass

    context = {
        'form': form,
        'title': 'Adaugă temă nouă',
    }

    return render(request, 'homework/homework_form.html', context)


@login_required
def homework_edit_view(request, homework_id):
    """Editare temă existentă"""
    homework = get_object_or_404(Homework, id=homework_id, user=request.user)

    if request.method == 'POST':
        form = HomeworkForm(user=request.user, data=request.POST, instance=homework)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tema "{homework.titlu}" a fost actualizată!')
            return redirect('homework:detail', homework_id=homework.id)
    else:
        form = HomeworkForm(instance=homework, user=request.user)

    context = {
        'form': form,
        'homework': homework,
        'title': f'Editează tema: {homework.titlu}',
    }

    return render(request, 'homework/homework_form.html', context)


@login_required
def homework_delete_view(request, homework_id):
    """Ștergere temă"""
    homework = get_object_or_404(Homework, id=homework_id, user=request.user)

    if request.method == 'POST':
        homework_title = homework.titlu
        homework.delete()
        messages.success(request, f'Tema "{homework_title}" a fost ștearsă!')
        return redirect('homework:list')

    # Informații despre dependențe
    dependencies = {
        'files_count': homework.files.count(),
        'sessions_count': homework.sessions.count(),
        'reminders_count': homework.reminders.count(),
    }

    context = {
        'homework': homework,
        'dependencies': dependencies,
    }

    return render(request, 'homework/homework_delete.html', context)


@login_required
def homework_complete_toggle(request, homework_id):
    """Toggle status finalizat/nefinalizat pentru temă"""
    homework = get_object_or_404(Homework, id=homework_id, user=request.user)

    if request.method == 'POST':
        if homework.finalizata:
            # Marchează ca nefinalizată
            homework.finalizata = False
            homework.data_finalizare = None
            homework.progres = max(0, homework.progres - 10)  # Reduce progresul cu 10%
            message = f'Tema "{homework.titlu}" a fost marcată ca nefinalizată.'
        else:
            # Marchează ca finalizată
            homework.marcheaza_finalizata()
            message = f'Felicitări! Tema "{homework.titlu}" a fost finalizată!'

            # Creează notificare
            Notification.objects.create(
                user=request.user,
                tip='tema',
                titlu='Temă finalizată!',
                mesaj=f'Ai finalizat tema "{homework.titlu}" la {homework.subject.nume}.'
            )

            # Email părinte pentru temă finalizată (dacă e activat în profil)
            try:
                profile = request.user.student_profile
                parent_email = getattr(profile, 'email_parinte', '')
                if send_email and profile.reminder_teme and parent_email:
                    send_email(
                        to_emails=[parent_email],
                        subject=f'Temă finalizată: {homework.subject.nume}',
                        html_content=f"""
                        <p>Bună,</p>
                        <p>Tema a fost marcată ca finalizată:</p>
                        <ul>
                          <li>Materie: {homework.subject.nume}</li>
                          <li>Titlu: {homework.titlu}</li>
                          <li>Termen: {homework.deadline}</li>
                          <li>Progres: 100%</li>
                        </ul>
                        """
                    )
            except Exception:
                pass

        homework.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'completed': homework.finalizata,
                'message': message,
                'progress': homework.progres
            })
        else:
            messages.success(request, message)

    return redirect('homework:detail', homework_id=homework.id)


@login_required
def homework_update_progress(request, homework_id):
    """Actualizare progres temă"""
    homework = get_object_or_404(Homework, id=homework_id, user=request.user)

    if request.method == 'POST':
        try:
            progress = int(request.POST.get('progress', homework.progres))
            progress = max(0, min(100, progress))  # Între 0 și 100

            homework.progres = progress
            if progress == 100 and not homework.finalizata:
                homework.marcheaza_finalizata()
            homework.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'progress': homework.progres,
                    'completed': homework.finalizata
                })
            else:
                messages.success(request, f'Progresul a fost actualizat la {progress}%.')
        except (ValueError, TypeError):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Progres invalid'})
            else:
                messages.error(request, 'Progres invalid.')

    return redirect('homework:detail', homework_id=homework.id)


@login_required
def homework_file_upload_view(request, homework_id):
    """Upload fișier pentru o temă"""
    homework = get_object_or_404(Homework, id=homework_id, user=request.user)

    if request.method == 'POST':
        form = HomeworkFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_obj = form.save(commit=False)
            file_obj.homework = homework
            file_obj.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'file_id': file_obj.id,
                    'file_name': file_obj.nume,
                    'file_url': file_obj.fisier.url,
                    'file_type': file_obj.get_tip_display()
                })
            else:
                messages.success(request, f'Fișierul "{file_obj.nume}" a fost încărcat!')
                return redirect('homework:detail', homework_id=homework.id)
    else:
        form = HomeworkFileForm()

    context = {
        'form': form,
        'homework': homework,
    }

    return render(request, 'homework/file_upload.html', context)


@login_required
def homework_file_delete_view(request, homework_id, file_id):
    """Ștergere fișier"""
    homework = get_object_or_404(Homework, id=homework_id, user=request.user)
    file_obj = get_object_or_404(HomeworkFile, id=file_id, homework=homework)

    if request.method == 'POST':
        file_name = file_obj.nume
        # Șterge fișierul fizic
        if file_obj.fisier:
            file_path = file_obj.fisier.path
            if os.path.exists(file_path):
                os.remove(file_path)

        file_obj.delete()
        messages.success(request, f'Fișierul "{file_name}" a fost șters!')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

    return redirect('homework:detail', homework_id=homework.id)


@login_required
def homework_session_start(request, homework_id):
    """Începe o sesiune de lucru"""
    homework = get_object_or_404(Homework, id=homework_id, user=request.user)

    # Verifică dacă mai există o sesiune activă
    active_session = homework.sessions.filter(sfarsit__isnull=True).first()
    if active_session:
        messages.warning(request, 'Există deja o sesiune activă pentru această temă!')
        return redirect('homework:detail', homework_id=homework.id)

    # Creează sesiunea nouă
    session = HomeworkSession.objects.create(
        homework=homework,
        progres_inainte=homework.progres
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'start_time': session.inceput.isoformat()
        })
    else:
        messages.success(request, 'Sesiunea de lucru a fost începută!')

    return redirect('homework:detail', homework_id=homework.id)


@login_required
def homework_session_end(request, homework_id, session_id):
    """Termină o sesiune de lucru"""
    homework = get_object_or_404(Homework, id=homework_id, user=request.user)
    session = get_object_or_404(HomeworkSession, id=session_id, homework=homework)

    if request.method == 'POST':
        if not session.sfarsit:
            # Progresul nou din form
            new_progress = request.POST.get('progress', homework.progres)
            try:
                new_progress = int(new_progress)
                new_progress = max(0, min(100, new_progress))
            except (ValueError, TypeError):
                new_progress = homework.progres

            # Note despre sesiune
            session_notes = request.POST.get('session_notes', '')
            session_difficulties = request.POST.get('session_difficulties', '')

            # Finalizează sesiunea
            session.progres_dupa = new_progress
            session.note_sesiune = session_notes
            session.dificultati_sesiune = session_difficulties
            session.finalizeaza_sesiune(new_progress)

            messages.success(request, f'Sesiunea de {session.durata_minute} minute a fost finalizată!')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'duration': session.durata_minute,
                    'progress': new_progress
                })

    return redirect('homework:detail', homework_id=homework.id)


@login_required
def homework_calendar_view(request):
    """Vedere calendar cu toate temele"""
    user = request.user

    # Obține luna și anul din URL
    month = int(request.GET.get('month', date.today().month))
    year = int(request.GET.get('year', date.today().year))

    # Calculează prima și ultima zi din lună
    from calendar import monthrange
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Temele din această lună
    homework_in_month = Homework.objects.filter(
        user=user,
        deadline__range=[first_day, last_day]
    ).select_related('subject')

    # Organizează temele pe zile (map zi -> listă teme)
    calendar_data = {}
    for hw in homework_in_month:
        d = hw.deadline.day
        calendar_data.setdefault(d, []).append(hw)

    # Construiește săptămânile pentru afișare (7 zile/linie)
    cal = calendar.Calendar(firstweekday=0)  # 0 = Luni
    weeks = []
    for week in cal.monthdayscalendar(year, month):
        # week: [0 dacă nu e în lună altfel zi (1..31)]
        week_cells = []
        for day_num in week:
            if day_num == 0:
                week_cells.append({
                    'day': None,
                    'homeworks': []
                })
            else:
                week_cells.append({
                    'day': day_num,
                    'homeworks': calendar_data.get(day_num, [])
                })
        weeks.append(week_cells)

    # Navegare luna anterioară/următoare
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    context = {
        'calendar_weeks': weeks,
        'current_month': month,
        'current_year': year,
        'month_name': [
            '', 'Ianuarie', 'Februarie', 'Martie', 'Aprilie', 'Mai', 'Iunie',
            'Iulie', 'August', 'Septembrie', 'Octombrie', 'Noiembrie', 'Decembrie'
        ][month],
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'days_in_month': monthrange(year, month)[1],
        'first_weekday': first_day.weekday(),  # 0=Luni, 6=Duminică
    }

    return render(request, 'homework/homework_calendar.html', context)


@login_required
def homework_stats_view(request):
    """Statistici detaliate despre teme"""
    user = request.user

    # Statistici generale
    total_homework = Homework.objects.filter(user=user)
    completed_homework = total_homework.filter(finalizata=True)

    general_stats = {
        'total': total_homework.count(),
        'completed': completed_homework.count(),
        'completion_rate': (completed_homework.count() / max(total_homework.count(), 1)) * 100,
        'average_time': completed_homework.aggregate(avg=Avg('timp_lucrat'))['avg'] or 0,
        'total_time': completed_homework.aggregate(sum=Sum('timp_lucrat'))['sum'] or 0,
    }

    # Statistici pe materii
    subject_stats = []
    subject_stats_js = []
    for subject in Subject.objects.filter(user=user, activa=True):
        subject_homework = total_homework.filter(subject=subject)
        subject_completed = subject_homework.filter(finalizata=True)

        subject_stats.append({
            'subject': subject,
            'total': subject_homework.count(),
            'completed': subject_completed.count(),
            'completion_rate': (subject_completed.count() / max(subject_homework.count(), 1)) * 100,
            'avg_time': subject_completed.aggregate(avg=Avg('timp_lucrat'))['avg'] or 0,
        })
        subject_stats_js.append({
            'subject_name': subject.nume,
            'total': subject_homework.count(),
            'completed': subject_completed.count(),
            'avg_time': float(subject_completed.aggregate(avg=Avg('timp_lucrat'))['avg'] or 0),
        })

    # Productivitate pe zile din săptămână (0=Luni..6=Duminică)
    from django.db.models.functions import ExtractWeekDay
    # ExtractWeekDay: în SQLite/Django, duminica poate fi 1; normalizăm la 0..6 cu un mapping
    raw_week = completed_homework.annotate(wd=ExtractWeekDay('data_finalizare')).values('wd').annotate(count=Count('id'))
    weekday_stats = []
    for item in raw_week:
        wd_val = int(item['wd'] or 0)
        # Django ExtractWeekDay: 1=Duminică ... 7=Sâmbătă
        normalized = (wd_val + 5) % 7  # 1->6, 2->0, 3->1, ..., 7->5
        weekday_stats.append({'weekday': normalized, 'count': item['count']})
    weekday_stats.sort(key=lambda x: x['weekday'])

    context = {
        'general_stats': general_stats,
        'subject_stats': subject_stats,
        'weekday_stats': weekday_stats,
        'subject_stats_json': json.dumps(subject_stats_js, cls=DjangoJSONEncoder),
        'weekday_stats_json': json.dumps(weekday_stats, cls=DjangoJSONEncoder),
    }

    return render(request, 'homework/homework_stats.html', context)