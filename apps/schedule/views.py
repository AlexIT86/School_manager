from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, time, datetime, timedelta
import json

from .models import ScheduleEntry, ScheduleTemplate, ScheduleTemplateEntry, ScheduleChange, ClassRoom, ClassScheduleEntry
from apps.homework.models import Homework
from .forms import (
    ScheduleEntryForm, ScheduleTemplateForm, ScheduleChangeForm, ScheduleImportForm,
    ClassRoomForm, ClassScheduleEntryForm
)
from django.core.exceptions import PermissionDenied
from apps.subjects.models import Subject
from apps.core.models import Notification
from apps.grades.models import Grade


def _propagate_class_entry_to_users(entry: ClassScheduleEntry):
    """Actualizează/creează intrarea din orar pentru toți elevii din clasa entry.class_room."""
    try:
        profiles = entry.class_room.students.select_related('user').all()
    except Exception:
        profiles = []
    for profile in profiles:
        subject, _ = Subject.objects.get_or_create(
            user=profile.user,
            nume=entry.subject_name,
            defaults={'culoare': entry.subject_color, 'activa': True}
        )
        ScheduleEntry.objects.update_or_create(
            user=profile.user,
            zi_saptamana=entry.zi_saptamana,
            numar_ora=entry.numar_ora,
            defaults={
                'subject': subject,
                'ora_inceput': entry.ora_inceput,
                'ora_sfarsit': entry.ora_sfarsit,
                'sala': entry.sala,
                'note': entry.note,
                'tip_ora': entry.tip_ora,
            }
        )


@login_required
def schedule_calendar_view(request):
    """Vedere principală calendar cu orarul săptămânal"""
    user = request.user

    # Obține intrările din orar pentru fiecare zi
    schedule_data = {}
    weekdays = ['Luni', 'Marți', 'Miercuri', 'Joi', 'Vineri']

    for day_num in range(1, 6):  # 1-5 (Luni-Vineri)
        day_name = weekdays[day_num - 1]
        entries = ScheduleEntry.objects.filter(
            user=user,
            zi_saptamana=day_num
        ).order_by('numar_ora').select_related('subject')

        schedule_data[day_name] = {
            'day_num': day_num,
            'entries': list(entries)
        }

    # Atașează temele nefinalizate per materie pentru a fi afișate în orar
    pending_map = {}
    pending_homework = Homework.objects.filter(user=user, finalizata=False).select_related('subject')
    for hw in pending_homework:
        pending_map.setdefault(hw.subject_id, []).append(hw)

    for day in schedule_data.values():
        for entry in day['entries']:
            # listă de Homework atașată fiecărei intrări din orar
            entry.pending_homework = pending_map.get(entry.subject_id, [])

    # Materii distincte pentru filtre (evită duplicatele)
    # Subiecte unice folosite în orar (bazat pe subject_id)
    subject_ids_qs = ScheduleEntry.objects.filter(user=user).values_list('subject_id', flat=True).distinct()
    subject_rows = Subject.objects.filter(id__in=subject_ids_qs).values('nume', 'culoare').order_by('nume')
    subject_filters = [{'name': row['nume'], 'color': row['culoare']} for row in subject_rows]

    # Număr de materii distincte per zi a săptămânii (pentru vizualizarea lunară)
    weekday_subject_counts = {}
    for day_num in range(1, 6):
        day_name = weekdays[day_num - 1]
        unique_subject_ids = {entry.subject_id for entry in schedule_data.get(day_name, {}).get('entries', [])}
        weekday_subject_counts[day_num] = len(unique_subject_ids)
    # weekend (Sâmbătă=6, Duminică=7)
    weekday_subject_counts[6] = 0
    weekday_subject_counts[7] = 0

    # Calculează orele disponibile și parametrii în funcție de profil
    max_hours = 8
    start_base = time(8, 0)
    class_duration = 50
    break_duration = 10
    try:
        if hasattr(user, 'student_profile') and user.student_profile:
            if getattr(user.student_profile, 'nr_ore_pe_zi', None):
                max_hours = user.student_profile.nr_ore_pe_zi
            if getattr(user.student_profile, 'ore_start', None):
                start_base = user.student_profile.ore_start
            if getattr(user.student_profile, 'durata_ora', None):
                class_duration = int(user.student_profile.durata_ora or 50)
            if getattr(user.student_profile, 'durata_pauza', None):
                break_duration = int(user.student_profile.durata_pauza or 10)
    except Exception:
        pass

    hour_slots = list(range(1, max_hours + 1))

    # Etichete de timp pentru fiecare oră pe baza profilului
    time_labels = []
    day_start_dt = datetime.combine(date.today(), start_base)
    slot_total = class_duration + break_duration
    for idx in range(max_hours):
        slot_start_dt = day_start_dt + timedelta(minutes=idx * slot_total)
        slot_end_dt = slot_start_dt + timedelta(minutes=class_duration)
        time_labels.append({'start': slot_start_dt.time(), 'end': slot_end_dt.time()})

    # Verifică modificări pentru săptămâna curentă
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Luni
    week_end = week_start + timedelta(days=4)  # Vineri

    current_changes = ScheduleChange.objects.filter(
        Q(data_end__isnull=True) | Q(data_end__gte=week_start),
        user=user,
        data_start__lte=week_end
    ).select_related('schedule_entry', 'subject_nou')

    # Informații despre săptămâna curentă
    week_info = {
        'start': week_start,
        'end': week_end,
        'current_day': today.isoweekday() if today.isoweekday() <= 5 else None,
        'changes': current_changes
    }

    # Statistici rapide
    # Busiest day weighted by subject rating
    busy_scores = {}
    for day_name, data in schedule_data.items():
        score = 0
        for entry in data['entries']:
            try:
                score += getattr(entry.subject, 'rating', 3) or 3
            except Exception:
                score += 3
        busy_scores[day_name] = score

    stats = {
        'total_hours_per_week': sum(len(day['entries']) for day in schedule_data.values()),
        'subjects_count': ScheduleEntry.objects.filter(user=user).values('subject').distinct().count(),
        'busiest_day': max(busy_scores, key=busy_scores.get) if busy_scores else None,
    }

    # Ora curentă pentru highlight în UI (în funcție de profil)
    current_hour = None
    now = datetime.now()
    if 1 <= now.isoweekday() <= 5:
        day_start = datetime.combine(now.date(), start_base)
        day_end = day_start + timedelta(minutes=slot_total * max_hours)
        if day_start <= now <= day_end:
            minutes_since_start = int((now - day_start).total_seconds() // 60)
            current_hour = min(max_hours, (minutes_since_start // slot_total) + 1)

    # Orele de azi (pentru secțiunea "Orele de astăzi")
    today_classes = []
    if 1 <= today.isoweekday() <= 5:
        today_classes = list(ScheduleEntry.objects.filter(
            user=user,
            zi_saptamana=today.isoweekday()
        ).order_by('numar_ora').select_related('subject'))

        # atașează și pentru lista de azi
        for entry in today_classes:
            entry.pending_homework = pending_map.get(entry.subject_id, [])

    context = {
        'schedule_data': schedule_data,
        'hour_slots': hour_slots,
        'time_labels': time_labels,
        'week_info': week_info,
        'stats': stats,
        'weekdays': weekdays,
        'current_hour': current_hour,
        'today_classes': today_classes,
        'subject_filters': subject_filters,
        # Parametri pentru UI/JS
        'start_hour': start_base.hour,
        'start_minute': start_base.minute,
        'duration_min': class_duration,
        'break_min': break_duration,
        'max_hours': max_hours,
        'weekday_subject_counts_json': json.dumps(weekday_subject_counts),
    }

    # Month events for client-side month view
    try:
        from calendar import monthrange
        today_local = date.today()
        year = int(request.GET.get('year', today_local.year))
        month = int(request.GET.get('month', today_local.month))
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        month_events = {}
        # Homework
        for hw in Homework.objects.filter(user=user, deadline__range=[first_day, last_day]).select_related('subject'):
            day_num = hw.deadline.day
            month_events.setdefault(day_num, []).append({
                'type': 'homework',
                'label': f"{hw.titlu}",
                'subject': hw.subject.nume,
                'color': '#ff6b6b',
                'url': f"/teme/{hw.id}/"
            })
        # Grades/Absences
        for gr in Grade.objects.filter(user=user, data__range=[first_day, last_day]).select_related('subject'):
            day_num = gr.data.day
            label = ''
            if gr.tip == 'nota':
                label = f"{gr.valoare}"
            else:
                label = gr.get_tip_display()
            month_events.setdefault(day_num, []).append({
                'type': 'grade',
                'label': label,
                'subject': gr.subject.nume,
                'color': '#f9ca24',
                'url': f"/note/{gr.id}/"
            })

        context['month_events_json'] = json.dumps(month_events)
        context['month_current'] = month
        context['year_current'] = year
    except Exception:
        context['month_events_json'] = '[]'

    return render(request, 'schedule/calendar.html', context)


@login_required
def schedule_entry_create_view(request):
    """Creare intrare nouă în orar"""
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method == 'POST':
        form = ScheduleEntryForm(user=request.user, data=request.POST)
        if form.is_valid():
            try:
                entry = form.save(commit=False)
                entry.user = request.user

                # Completează orele dacă lipsesc
                if not entry.ora_inceput or not entry.ora_sfarsit:
                    try:
                        base = request.user.student_profile.ore_start
                        durata = getattr(request.user.student_profile, 'durata_ora', 50) or 50
                        pauza = getattr(request.user.student_profile, 'durata_pauza', 10) or 10
                    except Exception:
                        from datetime import time as time_cls
                        base = time_cls(8, 0)
                        durata = 50
                        pauza = 10

                    offset = max(0, (entry.numar_ora - 1)) * (durata + pauza)
                    start_dt = datetime.combine(date.today(), base) + timedelta(minutes=offset)
                    end_dt = start_dt + timedelta(minutes=durata)
                    entry.ora_inceput = start_dt.time()
                    entry.ora_sfarsit = end_dt.time()

                # Preia sala implicit din materie dacă nu a fost furnizată
                if (not entry.sala) and getattr(entry, 'subject', None) and getattr(entry.subject, 'sala', ''):
                    entry.sala = entry.subject.sala

                entry.full_clean()  # Validează cu metodele custom din model
                entry.save()

                messages.success(request,
                                 f'Ora de {entry.subject.nume} a fost adăugată în {entry.get_zi_saptamana_display()}!')

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'entry_id': entry.id,
                        'entry_html': render_schedule_entry_html(entry)
                    })

                # Preserve view mode in redirect
                view_mode = request.GET.get('view') or request.POST.get('view')
                if view_mode == 'month':
                    return redirect(f"{reverse('schedule:calendar')}?view=month")
                return redirect('schedule:calendar')
            except ValidationError as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
                form.add_error(None, e.message)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': form.errors.get_json_data()}, status=400)
    else:
        form = ScheduleEntryForm(user=request.user)

        # Pre-populează din URL params
        day = request.GET.get('day')
        hour = request.GET.get('hour')
        subject_id = request.GET.get('subject')

        if day:
            form.initial['zi_saptamana'] = int(day)
        if hour:
            form.initial['numar_ora'] = int(hour)
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id, user=request.user)
                form.initial['subject'] = subject
            except Subject.DoesNotExist:
                pass

    context = {
        'form': form,
        'title': 'Adaugă oră în orar',
    }

    return render(request, 'schedule/entry_form.html', context)


@login_required
def schedule_entry_edit_view(request, entry_id):
    """Editare intrare din orar"""
    if not request.user.is_superuser:
        raise PermissionDenied
    entry = get_object_or_404(ScheduleEntry, id=entry_id, user=request.user)

    if request.method == 'POST':
        form = ScheduleEntryForm(user=request.user, data=request.POST, instance=entry)
        if form.is_valid():
            try:
                entry = form.save()
                messages.success(request, f'Ora de {entry.subject.nume} a fost actualizată!')

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'entry_html': render_schedule_entry_html(entry)
                    })

                view_mode = request.GET.get('view') or request.POST.get('view')
                if view_mode == 'month':
                    return redirect(f"{reverse('schedule:calendar')}?view=month")
                return redirect('schedule:calendar')
            except ValidationError as e:
                form.add_error(None, e.message)
    else:
        form = ScheduleEntryForm(instance=entry, user=request.user)

    context = {
        'form': form,
        'entry': entry,
        'title': f'Editează ora de {entry.subject.nume}',
    }

    return render(request, 'schedule/entry_form.html', context)


@login_required
def schedule_entry_delete_view(request, entry_id):
    """Ștergere intrare din orar"""
    if not request.user.is_superuser:
        raise PermissionDenied
    entry = get_object_or_404(ScheduleEntry, id=entry_id, user=request.user)

    if request.method == 'POST':
        subject_name = entry.subject.nume
        day_name = entry.get_zi_saptamana_display()
        entry.delete()

        messages.success(request, f'Ora de {subject_name} din {day_name} a fost ștearsă!')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        return redirect('schedule:calendar')

    context = {
        'entry': entry,
    }

    return render(request, 'schedule/entry_delete.html', context)


@login_required
def schedule_templates_view(request):
    """Lista template-urilor de orar"""
    templates = ScheduleTemplate.objects.filter(user=request.user).order_by('-activ', '-updated_at')

    context = {
        'templates': templates,
    }

    return render(request, 'schedule/templates.html', context)


@login_required
def schedule_template_create_view(request):
    """Creare template nou de orar"""
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method == 'POST':
        form = ScheduleTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.user = request.user
            template.save()

            # Copiază orarul curent în template dacă există
            current_entries = ScheduleEntry.objects.filter(user=request.user)
            for entry in current_entries:
                ScheduleTemplateEntry.objects.create(
                    template=template,
                    subject=entry.subject,
                    zi_saptamana=entry.zi_saptamana,
                    ora_inceput=entry.ora_inceput,
                    ora_sfarsit=entry.ora_sfarsit,
                    sala=entry.sala,
                    note=entry.note,
                    numar_ora=entry.numar_ora,
                    tip_ora=entry.tip_ora
                )

            messages.success(request, f'Template-ul "{template.nume}" a fost creat cu orarul curent!')
            return redirect('schedule:templates')
    else:
        form = ScheduleTemplateForm()

    context = {
        'form': form,
        'title': 'Creare template orar',
    }

    return render(request, 'schedule/template_form.html', context)


@login_required
def schedule_template_apply_view(request, template_id):
    """Aplicare template de orar"""
    if not request.user.is_superuser:
        raise PermissionDenied
    template = get_object_or_404(ScheduleTemplate, id=template_id, user=request.user)

    if request.method == 'POST':
        # Confirmă aplicarea template-ului
        template.aplicare_template()

        messages.success(request, f'Template-ul "{template.nume}" a fost aplicat cu succes!')
        return redirect('schedule:calendar')

    # Informații pentru confirmare
    current_entries_count = ScheduleEntry.objects.filter(user=request.user).count()
    template_entries_count = template.template_entries.count()

    context = {
        'template': template,
        'current_entries_count': current_entries_count,
        'template_entries_count': template_entries_count,
    }

    return render(request, 'schedule/template_apply.html', context)


@login_required
def schedule_template_delete_view(request, template_id):
    """Ștergere template de orar"""
    if not request.user.is_superuser:
        raise PermissionDenied
    template = get_object_or_404(ScheduleTemplate, id=template_id, user=request.user)

    if request.method == 'POST':
        template_name = template.nume
        template.delete()
        messages.success(request, f'Template-ul "{template_name}" a fost șters!')
        return redirect('schedule:templates')

    context = {
        'template': template,
    }

    return render(request, 'schedule/template_delete.html', context)


@login_required
def schedule_changes_view(request):
    """Lista modificărilor în orar"""
    changes = ScheduleChange.objects.filter(user=request.user).order_by('-data_start')

    # Filtrare după perioada
    period = request.GET.get('period', 'current')
    today = date.today()

    if period == 'current':
        # Modificările active acum
        changes = changes.filter(
            Q(data_end__isnull=True) | Q(data_end__gte=today),
            data_start__lte=today
        )
    elif period == 'future':
        # Modificările viitoare
        changes = changes.filter(data_start__gt=today)
    elif period == 'past':
        # Modificările trecute
        changes = changes.filter(data_end__lt=today)

    context = {
        'changes': changes,
        'current_period': period,
    }

    return render(request, 'schedule/changes.html', context)


@login_required
def schedule_change_create_view(request):
    """Creare modificare în orar"""
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method == 'POST':
        form = ScheduleChangeForm(request.POST, user=request.user)
        if form.is_valid():
            change = form.save(commit=False)
            change.user = request.user
            change.save()

            # Creează notificare
            Notification.objects.create(
                user=request.user,
                tip='sistem',
                titlu='Modificare orar',
                mesaj=f'A fost adăugată o modificare: {change.get_tip_schimbare_display()} pentru {change.schedule_entry.subject.nume}'
            )

            messages.success(request, 'Modificarea a fost adăugată cu succes!')
            return redirect('schedule:changes')
    else:
        form = ScheduleChangeForm(user=request.user)

        # Pre-populează din URL
        entry_id = request.GET.get('entry')
        if entry_id:
            try:
                entry = ScheduleEntry.objects.get(id=entry_id, user=request.user)
                form.initial['schedule_entry'] = entry
            except ScheduleEntry.DoesNotExist:
                pass

    context = {
        'form': form,
        'title': 'Adaugă modificare orar',
    }

    return render(request, 'schedule/change_form.html', context)


@login_required
def schedule_change_delete_view(request, change_id):
    """Ștergere modificare din orar"""
    if not request.user.is_superuser:
        raise PermissionDenied
    change = get_object_or_404(ScheduleChange, id=change_id, user=request.user)

    if request.method == 'POST':
        change.delete()
        messages.success(request, 'Modificarea a fost ștearsă!')
        return redirect('schedule:changes')

    context = {
        'change': change,
    }

    return render(request, 'schedule/change_delete.html', context)


@login_required
def schedule_print_view(request):
    """Versiune pentru printare a orarului"""
    user = request.user

    # Orarul complet
    schedule_data = {}
    weekdays = ['Luni', 'Marți', 'Miercuri', 'Joi', 'Vineri']

    for day_num in range(1, 6):
        day_name = weekdays[day_num - 1]
        entries = ScheduleEntry.objects.filter(
            user=user,
            zi_saptamana=day_num
        ).order_by('numar_ora').select_related('subject')

        schedule_data[day_name] = list(entries)

    # Informații student + parametrizare oră/pausă
    profile = getattr(user, 'student_profile', None)
    max_hours = 8
    start_base = time(8, 0)
    class_duration = 50
    break_duration = 10
    try:
        if profile:
            if getattr(profile, 'nr_ore_pe_zi', None):
                max_hours = int(profile.nr_ore_pe_zi)
            if getattr(profile, 'ore_start', None):
                start_base = profile.ore_start
            if getattr(profile, 'durata_ora', None):
                class_duration = int(profile.durata_ora or 50)
            if getattr(profile, 'durata_pauza', None):
                break_duration = int(profile.durata_pauza or 10)
    except Exception:
        pass

    # Fallback: dacă există o oră mai mare în date, folosește acea limită
    try:
        data_max = 0
        for day_entries in schedule_data.values():
            for e in day_entries:
                if getattr(e, 'numar_ora', 0) and int(e.numar_ora) > data_max:
                    data_max = int(e.numar_ora)
        if data_max > 0:
            max_hours = max(max_hours, data_max)
    except Exception:
        pass

    # Etichete de timp pentru rândurile din tabelul compact
    time_labels = []
    try:
        from datetime import datetime as dt
        day_start_dt = dt.combine(date.today(), start_base)
        slot_total = class_duration + break_duration
        for idx in range(max_hours):
            slot_start_dt = day_start_dt + timedelta(minutes=idx * slot_total)
            slot_end_dt = slot_start_dt + timedelta(minutes=class_duration)
            time_labels.append({'start': slot_start_dt.time(), 'end': slot_end_dt.time()})
    except Exception:
        # fallback gol dacă apare vreo problemă
        time_labels = []

    context = {
        'schedule_data': schedule_data,
        'weekdays': weekdays,
        'profile': profile,
        'print_date': date.today(),
        'max_hours': max_hours,
        'time_labels': time_labels,
        'hour_slots': list(range(1, max_hours + 1)),
    }

    return render(request, 'schedule/print.html', context)


@login_required
def schedule_today_view(request):
    """Orarul de astăzi - widget pentru dashboard"""
    user = request.user
    today = date.today()
    weekday = today.isoweekday()

    if weekday <= 5:  # Luni-Vineri
        entries = ScheduleEntry.objects.filter(
            user=user,
            zi_saptamana=weekday
        ).order_by('numar_ora').select_related('subject')

        # Verifică modificări pentru astăzi
        changes = ScheduleChange.objects.filter(
            Q(data_end__isnull=True) | Q(data_end__gte=today),
            user=user,
            data_start__lte=today
        ).select_related('schedule_entry')

        # Aplică modificările la intrări
        modified_entries = []
        for entry in entries:
            entry_changes = [c for c in changes if c.schedule_entry == entry]
            if entry_changes:
                # Folosește ultima modificare
                change = entry_changes[-1]
                entry.current_change = change
            modified_entries.append(entry)

        entries = modified_entries
    else:
        entries = []

    # Ora curentă pentru highlighting
    current_time = datetime.now().time()

    context = {
        'entries': entries,
        'weekday_name': ['Luni', 'Marți', 'Miercuri', 'Joi', 'Vineri', 'Sâmbătă', 'Duminică'][weekday - 1],
        'current_time': current_time,
        'is_weekend': weekday > 5,
    }

    return render(request, 'schedule/today_widget.html', context)


@login_required
def schedule_quick_edit_view(request):
    """Editor rapid pentru orar - AJAX"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permisiune insuficientă'}, status=403)
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'move_entry':
            # Mută o intrare la altă oră/zi
            entry_id = request.POST.get('entry_id')
            new_day = int(request.POST.get('new_day'))
            new_hour = int(request.POST.get('new_hour'))

            try:
                entry = ScheduleEntry.objects.get(id=entry_id, user=request.user)

                # Verifică dacă noua poziție este liberă
                existing = ScheduleEntry.objects.filter(
                    user=request.user,
                    zi_saptamana=new_day,
                    numar_ora=new_hour
                ).exclude(id=entry_id).first()

                if existing:
                    return JsonResponse({
                        'success': False,
                        'error': f'Ora {new_hour} din {entry.get_zi_saptamana_display()} este deja ocupată de {existing.subject.nume}'
                    })

                entry.zi_saptamana = new_day
                entry.numar_ora = new_hour
                entry.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Ora de {entry.subject.nume} a fost mutată cu succes!'
                })

            except ScheduleEntry.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Intrarea nu a fost găsită'})
            except ValidationError as e:
                return JsonResponse({'success': False, 'error': str(e)})

        elif action == 'duplicate_day':
            # Duplică orarul unei zile la alta
            source_day = int(request.POST.get('source_day'))
            target_day = int(request.POST.get('target_day'))

            # Șterge orarul existent din ziua țintă
            ScheduleEntry.objects.filter(
                user=request.user,
                zi_saptamana=target_day
            ).delete()

            # Copiază intrările
            source_entries = ScheduleEntry.objects.filter(
                user=request.user,
                zi_saptamana=source_day
            )

            for entry in source_entries:
                ScheduleEntry.objects.create(
                    user=request.user,
                    subject=entry.subject,
                    zi_saptamana=target_day,
                    ora_inceput=entry.ora_inceput,
                    ora_sfarsit=entry.ora_sfarsit,
                    sala=entry.sala,
                    note=entry.note,
                    numar_ora=entry.numar_ora,
                    tip_ora=entry.tip_ora
                )

            return JsonResponse({
                'success': True,
                'message': f'Orarul a fost copiat cu succes!'
            })

    return JsonResponse({'success': False, 'error': 'Acțiune invalidă'})


def render_schedule_entry_html(entry):
    """Helper function pentru a renda HTML-ul unei intrări"""
    # Aceasta ar putea fi implementată cu un template fragment
    return f"""
    <div class="schedule-entry" style="background-color: {entry.subject.culoare}20; border-left: 4px solid {entry.subject.culoare};">
        <strong>{entry.subject.nume}</strong><br>
        <small>{entry.ora_inceput.strftime('%H:%M')} - {entry.ora_sfarsit.strftime('%H:%M')}</small>
        {f'<br><small>Sala: {entry.sala}</small>' if entry.sala else ''}
    </div>
    """


# --- Clase și orar pe clasă (admin intern - protejăm în UI pentru superadmin) ---
@login_required
def classroom_list_view(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    classes = ClassRoom.objects.all().order_by('nume')
    return render(request, 'schedule/classes.html', {'classes': classes})


@login_required
def classroom_create_view(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method == 'POST':
        form = ClassRoomForm(request.POST)
        if form.is_valid():
            classroom = form.save()
            messages.success(request, f'Clasa {classroom.nume} a fost creată!')
            return redirect('schedule:classes')
    else:
        form = ClassRoomForm()
    return render(request, 'schedule/schedule_form.html', {'form': form, 'title': 'Creare clasă'})


@login_required
def classroom_edit_view(request, class_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    classroom = get_object_or_404(ClassRoom, id=class_id)
    if request.method == 'POST':
        form = ClassRoomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, f'Clasa {classroom.nume} a fost actualizată!')
            return redirect('schedule:classes')
    else:
        form = ClassRoomForm(instance=classroom)
    return render(request, 'schedule/schedule_form.html', {'form': form, 'title': f'Editează clasa {classroom.nume}'})


@login_required
def classroom_delete_view(request, class_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    classroom = get_object_or_404(ClassRoom, id=class_id)
    if request.method == 'POST':
        name = classroom.nume
        classroom.delete()
        messages.success(request, f'Clasa {name} a fost ștearsă!')
        return redirect('schedule:classes')
    return render(request, 'schedule/template_delete.html', {'template': classroom})


@login_required
def class_schedule_view(request, class_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    classroom = get_object_or_404(ClassRoom, id=class_id)
    weekdays = ['Luni', 'Marți', 'Miercuri', 'Joi', 'Vineri']
    data = {}
    for day_num in range(1, 6):
        entries = ClassScheduleEntry.objects.filter(class_room=classroom, zi_saptamana=day_num).order_by('numar_ora')
        data[weekdays[day_num - 1]] = list(entries)
    return render(request, 'schedule/class_schedule.html', {
        'classroom': classroom,
        'schedule_data': data,
        'weekdays': weekdays,
    })


@login_required
def class_schedule_import_from_user(request, class_id):
    """Importă orarul utilizatorului curent ca template de clasă (doar superadmin)."""
    if not request.user.is_superuser:
        raise PermissionDenied
    classroom = get_object_or_404(ClassRoom, id=class_id)

    # Șterge orarul de clasă existent
    ClassScheduleEntry.objects.filter(class_room=classroom).delete()

    # Copiază din orarul userului curent
    entries = ScheduleEntry.objects.filter(user=request.user).order_by('zi_saptamana', 'numar_ora')
    for e in entries:
        ClassScheduleEntry.objects.create(
            class_room=classroom,
            zi_saptamana=e.zi_saptamana,
            numar_ora=e.numar_ora,
            ora_inceput=e.ora_inceput,
            ora_sfarsit=e.ora_sfarsit,
            subject_name=e.subject.nume,
            subject_color=e.subject.culoare,
            sala=e.sala,
            note=e.note,
            tip_ora=e.tip_ora,
        )

    messages.success(request, f'Orarul tău a fost importat pentru clasa {classroom.nume}.')
    return redirect('schedule:class_schedule', class_id=classroom.id)


@login_required
def class_schedule_entry_create_view(request, class_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    classroom = get_object_or_404(ClassRoom, id=class_id)
    if request.method == 'POST':
        form = ClassScheduleEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.class_room = classroom
            entry.save()
            _propagate_class_entry_to_users(entry)
            messages.success(request, 'Ora a fost adăugată în orarul clasei!')
            return redirect('schedule:class_schedule', class_id=classroom.id)
    else:
        form = ClassScheduleEntryForm()
    return render(request, 'schedule/entry_form.html', {'form': form, 'title': f'Adaugă oră pentru {classroom.nume}'})


@login_required
def class_schedule_entry_edit_view(request, class_id, entry_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    classroom = get_object_or_404(ClassRoom, id=class_id)
    entry = get_object_or_404(ClassScheduleEntry, id=entry_id, class_room=classroom)
    if request.method == 'POST':
        form = ClassScheduleEntryForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save()
            _propagate_class_entry_to_users(entry)
            messages.success(request, 'Ora a fost actualizată!')
            return redirect('schedule:class_schedule', class_id=classroom.id)
    else:
        form = ClassScheduleEntryForm(instance=entry)
    return render(request, 'schedule/entry_form.html', {'form': form, 'title': f'Editează oră pentru {classroom.nume}'})


@login_required
def class_schedule_entry_delete_view(request, class_id, entry_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    classroom = get_object_or_404(ClassRoom, id=class_id)
    entry = get_object_or_404(ClassScheduleEntry, id=entry_id, class_room=classroom)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Ora a fost ștearsă!')
        return redirect('schedule:class_schedule', class_id=classroom.id)
    return render(request, 'schedule/entry_delete.html', {'entry': entry})


@login_required
def school_year_2025_2026_view(request):
    """Structura anului școlar 2025-2026 (module, vacanțe, excepții)."""
    context = {
        'general': {
            'durata_saptamani': 36,
            'perioada': ('2025-09-08', '2026-06-19'),
            'structura': '5 module + 5 vacanțe',
        },
        'exceptii': [
            {'clase': 'Clasa a XII-a zi, a XIII-a seral/frecvență redusă', 'pana_la': '2026-06-05', 'saptamani': 34},
            {'clase': 'Clasa a VIII-a', 'pana_la': '2026-06-12', 'saptamani': 35},
            {'clase': 'Liceal filiera tehnologică', 'pana_la': '2026-06-26', 'saptamani': 37},
            {'clase': 'Postliceal', 'nota': 'Durata conform planurilor-cadru în vigoare'},
        ],
        'module': [
            {'nr': 1, 'inceput': '2025-09-08', 'sfarsit': '2025-10-24'},
            {'nr': 2, 'inceput': '2025-11-03', 'sfarsit': '2025-12-19'},
            {'nr': 3, 'inceput': '2026-01-08', 'sfarsit_variant': ['2026-02-06', '2026-02-13', '2026-02-20']},
            {'nr': 4, 'inceput_variant': ['2026-02-16', '2026-02-23', '2026-03-02'], 'sfarsit': '2026-04-03'},
            {'nr': 5, 'inceput': '2026-04-15', 'sfarsit': '2026-06-19'},
        ],
        'vacante': {
            'toamna': ('2025-10-25', '2025-11-02'),
            'iarna': ('2025-12-20', '2026-01-07'),
            'primavara': ('2026-04-04', '2026-04-14'),
            'vara': ('2026-06-20', '2026-09-06'),
            'februarie_mobila_interval': ('2026-02-09', '2026-03-01'),
            'februarie_distributie': {
                '2026-02-09:2026-02-15': ['Cluj', 'Timiș', 'Bistrița-Năsăud'],
                '2026-02-16:2026-02-22': ['București', 'Ilfov', 'Sălaj', 'Bihor', 'Arad', 'Iași', 'Hunedoara', 'Brașov', 'Caraș-Severin', 'Gorj', 'Vâlcea', 'Argeș', 'Dâmbovița', 'Prahova', 'Buzău', 'Tulcea', 'Mehedinți', 'Dolj', 'Olt', 'Teleorman', 'Ialomița', 'Călărași'],
                '2026-02-23:2026-03-01': ['Satu-Mare', 'Maramureș', 'Suceava', 'Botoșani', 'Alba', 'Sibiu', 'Mureș', 'Harghita', 'Neamț', 'Covasna', 'Bacău', 'Vrancea', 'Vaslui', 'Galați', 'Brăila', 'Giurgiu', 'Constanța'],
            },
        },
        'programe_speciale': {
            'interval': ('2025-09-08', '2026-04-03'),
            'durata_zile': 5,
            'descriere': '"Școala altfel" și "Săptămâna verde" - la decizia unității',
        },
    }
    return render(request, 'schedule/school_year_2025_2026.html', context)