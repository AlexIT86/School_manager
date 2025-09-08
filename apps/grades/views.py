from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Avg, Max, Min
from django.core.paginator import Paginator
from datetime import date, timedelta
import json

from .models import Grade, Semester, SubjectGradeStats, GradeGoal
from .forms import GradeForm, SemesterForm, GradeGoalForm, GradeFilterForm
from apps.subjects.models import Subject
from apps.core.models import Notification


@login_required
def grades_overview_view(request):
    """Vedere generală pentru note și absențe"""
    user = request.user

    # Semestrul activ
    active_semester = Semester.objects.filter(user=user, activ=True).first()
    if not active_semester:
        # Creează semestrul curent dacă nu există
        current_year = date.today().year
        semester_num = 1 if date.today().month < 6 else 2
        active_semester = Semester.objects.create(
            user=user,
            numar=semester_num,
            an_scolar=f"{current_year}-{current_year + 1}",
            data_inceput=date(current_year, 9, 15) if semester_num == 1 else date(current_year, 2, 1),
            data_sfarsit=date(current_year + 1, 1, 31) if semester_num == 1 else date(current_year, 6, 15),
            activ=True
        )

    # Note recente (ultimele 10)
    recent_grades = Grade.objects.filter(
        user=user,
        tip='nota'
    ).order_by('-data')[:10]

    # Absențe recente (ultimele 10)
    recent_absences = Grade.objects.filter(
        user=user,
        tip__in=['absenta', 'absenta_motivata']
    ).order_by('-data')[:10]

    # Statistici per materie pentru semestrul activ
    subject_stats = []
    for subject in Subject.objects.filter(user=user, activa=True):
        stats, created = SubjectGradeStats.objects.get_or_create(
            user=user,
            subject=subject,
            semester=active_semester
        )
        # Recalculează mereu pentru a reflecta cele mai noi note
        stats.calculeaza_statistici()

        subject_stats.append(stats)

    # Obiective de note
    grade_goals = GradeGoal.objects.filter(
        user=user,
        semester=active_semester
    ).select_related('subject')

    # Statistici generale
    general_stats = {
        'total_grades': Grade.objects.filter(user=user, tip='nota').count(),
        'avg_grade': Grade.objects.filter(user=user, tip='nota').aggregate(avg=Avg('valoare'))['avg'] or 0,
        'total_absences': Grade.objects.filter(user=user, tip__in=['absenta', 'absenta_motivata']).count(),
        'motivated_absences': Grade.objects.filter(user=user, tip='absenta_motivata').count(),
        'grades_this_month': Grade.objects.filter(
            user=user,
            tip='nota',
            data__month=date.today().month,
            data__year=date.today().year
        ).count(),
    }

    context = {
        'active_semester': active_semester,
        'recent_grades': recent_grades,
        'recent_absences': recent_absences,
        'subject_stats': subject_stats,
        'grade_goals': grade_goals,
        'general_stats': general_stats,
    }

    return render(request, 'grades/overview.html', context)


@login_required
def grades_list_view(request):
    """Lista tuturor notelor cu filtrare"""
    user = request.user

    # Form pentru filtrare
    filter_form = GradeFilterForm(data=request.GET, user=user)

    # Queryset de bază
    grades = Grade.objects.filter(user=user)

    # Aplicare filtre
    if filter_form.is_valid():
        subject = filter_form.cleaned_data.get('subject')
        grade_type = filter_form.cleaned_data.get('grade_type')
        semester = filter_form.cleaned_data.get('semester')
        date_range = filter_form.cleaned_data.get('date_range')
        min_grade = filter_form.cleaned_data.get('min_grade')
        max_grade = filter_form.cleaned_data.get('max_grade')

        if subject:
            grades = grades.filter(subject=subject)

        if grade_type:
            grades = grades.filter(tip=grade_type)

        if semester:
            grades = grades.filter(semestru=semester)

        if date_range == 'this_week':
            start_week = date.today() - timedelta(days=date.today().weekday())
            grades = grades.filter(data__gte=start_week)
        elif date_range == 'this_month':
            grades = grades.filter(data__month=date.today().month, data__year=date.today().year)
        elif date_range == 'last_month':
            last_month = date.today().replace(day=1) - timedelta(days=1)
            grades = grades.filter(data__month=last_month.month, data__year=last_month.year)

        if min_grade:
            grades = grades.filter(valoare__gte=min_grade)

        if max_grade:
            grades = grades.filter(valoare__lte=max_grade)

    # Sortare
    sort_by = request.GET.get('sort', '-data')
    grades = grades.order_by(sort_by)

    # Paginare
    paginator = Paginator(grades, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'current_sort': sort_by,
    }

    return render(request, 'grades/grades_list.html', context)


@login_required
def grade_create_view(request):
    """Adăugare notă/absență nouă"""
    if request.method == 'POST':
        form = GradeForm(data=request.POST, user=request.user)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.user = request.user
            grade.save()

            # Actualizează statisticile pentru materie
            if grade.tip == 'nota':
                # Determină obiectul Semester corespunzător numărului din notă
                semester_obj = Semester.objects.filter(user=request.user, activ=True, numar=grade.semestru).first()
                if not semester_obj:
                    semester_obj = Semester.objects.filter(user=request.user, numar=grade.semestru).order_by('-an_scolar').first()
                if not semester_obj:
                    # Creează un semestru minim dacă lipsește
                    current_year = date.today().year
                    semester_obj = Semester.objects.create(
                        user=request.user,
                        numar=grade.semestru,
                        an_scolar=f"{current_year}-{current_year + 1}",
                        data_inceput=date(current_year, 9, 15) if grade.semestru == 1 else date(current_year, 2, 1),
                        data_sfarsit=date(current_year + (1 if grade.semestru == 1 else 0), 1 if grade.semestru == 1 else 6, 31 if grade.semestru == 1 else 15),
                        activ=False
                    )

                stats, created = SubjectGradeStats.objects.get_or_create(
                    user=request.user,
                    subject=grade.subject,
                    semester=semester_obj
                )
                stats.calculeaza_statistici()

                # Verifică obiectivele
                goals = GradeGoal.objects.filter(
                    user=request.user,
                    subject=grade.subject,
                    semester_id=grade.semestru
                )
                for goal in goals:
                    goal.verifica_obiectiv()

                # Creează notificare pentru note mari/mici
                if grade.valoare >= 9:
                    Notification.objects.create(
                        user=request.user,
                        tip='nota',
                        titlu='Notă excelentă!',
                        mesaj=f'Felicitări! Ai primit {grade.valoare} la {grade.subject.nume}!'
                    )
                elif grade.valoare < 5:
                    Notification.objects.create(
                        user=request.user,
                        tip='nota',
                        titlu='Atenție la nota slabă',
                        mesaj=f'Ai primit {grade.valoare} la {grade.subject.nume}. E timpul să lucrezi mai mult!'
                    )

            type_display = grade.get_tip_display()
            messages.success(request, f'{type_display} la {grade.subject.nume} a fost adăugată!')

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'grade_id': grade.id,
                    'redirect_url': f'/note/{grade.id}/'
                })

            return redirect('grades:detail', grade_id=grade.id)
    else:
        form = GradeForm(user=request.user)

        # Pre-populează cu materia din URL
        subject_id = request.GET.get('subject')
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id, user=request.user)
                form.initial['subject'] = subject
            except Subject.DoesNotExist:
                pass

    context = {
        'form': form,
        'title': 'Adaugă notă/absență',
    }

    return render(request, 'grades/grade_form.html', context)


@login_required
def grade_detail_view(request, grade_id):
    """Detalii despre o notă/absență"""
    grade = get_object_or_404(Grade, id=grade_id, user=request.user)

    # Alte note la aceeași materie (pentru context)
    related_grades = Grade.objects.filter(
        user=request.user,
        subject=grade.subject,
        tip='nota'
    ).exclude(id=grade.id).order_by('-data')[:5]

    # Statistici pentru materie
    subject_stats = None
    if grade.tip == 'nota':
        try:
            subject_stats = SubjectGradeStats.objects.get(
                user=request.user,
                subject=grade.subject,
                semester_id=grade.semestru
            )
        except SubjectGradeStats.DoesNotExist:
            pass

    context = {
        'grade': grade,
        'related_grades': related_grades,
        'subject_stats': subject_stats,
    }

    return render(request, 'grades/grade_detail.html', context)


@login_required
def grade_edit_view(request, grade_id):
    """Editare notă/absență"""
    grade = get_object_or_404(Grade, id=grade_id, user=request.user)

    if request.method == 'POST':
        form = GradeForm(data=request.POST, instance=grade, user=request.user)
        if form.is_valid():
            form.save()

            # Recalculează statisticile
            if grade.tip == 'nota':
                semester_obj = Semester.objects.filter(user=request.user, activ=True, numar=grade.semestru).first()
                if not semester_obj:
                    semester_obj = Semester.objects.filter(user=request.user, numar=grade.semestru).order_by('-an_scolar').first()
                if semester_obj:
                    try:
                        stats = SubjectGradeStats.objects.get(
                            user=request.user,
                            subject=grade.subject,
                            semester=semester_obj
                        )
                        stats.calculeaza_statistici()
                    except SubjectGradeStats.DoesNotExist:
                        pass

            messages.success(request, f'{grade.get_tip_display()} a fost actualizată!')
            return redirect('grades:detail', grade_id=grade.id)
    else:
        form = GradeForm(instance=grade, user=request.user)

    context = {
        'form': form,
        'grade': grade,
        'title': f'Editează {grade.get_tip_display().lower()}',
    }

    return render(request, 'grades/grade_form.html', context)


@login_required
def grade_delete_view(request, grade_id):
    """Ștergere notă/absență"""
    grade = get_object_or_404(Grade, id=grade_id, user=request.user)

    if request.method == 'POST':
        subject = grade.subject
        semestru = grade.semestru
        grade_type = grade.get_tip_display()

        grade.delete()

        # Recalculează statisticile
        semester_obj = Semester.objects.filter(user=request.user, activ=True, numar=semestru).first()
        if not semester_obj:
            semester_obj = Semester.objects.filter(user=request.user, numar=semestru).order_by('-an_scolar').first()
        if semester_obj:
            try:
                stats = SubjectGradeStats.objects.get(
                    user=request.user,
                    subject=subject,
                    semester=semester_obj
                )
                stats.calculeaza_statistici()
            except SubjectGradeStats.DoesNotExist:
                pass

        messages.success(request, f'{grade_type} a fost ștearsă!')
        return redirect('grades:overview')

    context = {
        'grade': grade,
    }

    return render(request, 'grades/grade_delete.html', context)


@login_required
def subject_grades_view(request, subject_id):
    """Toate notele pentru o materie specifică"""
    subject = get_object_or_404(Subject, id=subject_id, user=request.user)

    # Toate notele pentru această materie
    grades = Grade.objects.filter(
        user=request.user,
        subject=subject
    ).order_by('-data')

    # Statistici pentru materie
    active_semester = Semester.objects.filter(user=request.user, activ=True).first()
    subject_stats = None
    if active_semester:
        try:
            subject_stats = SubjectGradeStats.objects.get(
                user=request.user,
                subject=subject,
                semester=active_semester
            )
        except SubjectGradeStats.DoesNotExist:
            pass

    # Separare pe tipuri
    notes = grades.filter(tip='nota')
    absences = grades.filter(tip__in=['absenta', 'absenta_motivata'])

    context = {
        'subject': subject,
        'notes': notes,
        'absences': absences,
        'subject_stats': subject_stats,
    }

    return render(request, 'grades/subject_grades.html', context)


@login_required
def semesters_view(request):
    """Gestionare semestre"""
    semesters = Semester.objects.filter(user=request.user).order_by('-an_scolar', '-numar')

    context = {
        'semesters': semesters,
    }

    return render(request, 'grades/semesters.html', context)


@login_required
def semester_create_view(request):
    """Creare semestru nou"""
    if request.method == 'POST':
        form = SemesterForm(request.POST)
        if form.is_valid():
            semester = form.save(commit=False)
            semester.user = request.user
            semester.save()

            messages.success(request, f'Semestrul {semester.numar} - {semester.an_scolar} a fost creat!')
            return redirect('grades:semesters')
    else:
        form = SemesterForm()

    context = {
        'form': form,
        'title': 'Creare semestru nou',
    }

    return render(request, 'grades/semester_form.html', context)


@login_required
def grade_goals_view(request):
    """Gestionare obiective de note"""
    active_semester = Semester.objects.filter(user=request.user, activ=True).first()

    goals = GradeGoal.objects.filter(
        user=request.user,
        semester=active_semester
    ).select_related('subject') if active_semester else []

    context = {
        'goals': goals,
        'active_semester': active_semester,
    }

    return render(request, 'grades/grade_goals.html', context)


@login_required
def grade_goal_create_view(request):
    """Creare obiectiv de notă"""
    if request.method == 'POST':
        form = GradeGoalForm(data=request.POST, user=request.user)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()

            messages.success(request, f'Obiectivul pentru {goal.subject.nume} a fost creat!')
            return redirect('grades:goals')
    else:
        form = GradeGoalForm(user=request.user)

    context = {
        'form': form,
        'title': 'Creare obiectiv de notă',
    }

    return render(request, 'grades/goal_form.html', context)


@login_required
def grade_goal_edit_view(request, goal_id):
    """Editare obiectiv de notă"""
    goal = get_object_or_404(GradeGoal, id=goal_id, user=request.user)

    if request.method == 'POST':
        form = GradeGoalForm(data=request.POST, instance=goal, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Obiectivul pentru {goal.subject.nume} a fost actualizat!')
            return redirect('grades:goals')
    else:
        form = GradeGoalForm(instance=goal, user=request.user)

    context = {
        'form': form,
        'goal': goal,
        'title': f'Editează obiectiv - {goal.subject.nume}',
    }

    return render(request, 'grades/goal_form.html', context)


@login_required
def grade_goal_delete_view(request, goal_id):
    """Ștergere obiectiv de notă"""
    goal = get_object_or_404(GradeGoal, id=goal_id, user=request.user)

    if request.method == 'POST':
        subject_name = goal.subject.nume
        goal.delete()
        messages.success(request, f'Obiectivul pentru {subject_name} a fost șters!')
        return redirect('grades:goals')

    context = {
        'goal': goal,
    }

    return render(request, 'grades/goal_delete.html', context)


@login_required
def grades_stats_view(request):
    """Statistici detaliate pentru note"""
    user = request.user

    # Statistici generale
    all_grades = Grade.objects.filter(user=user, tip='nota')
    general_stats = {
        'total_grades': all_grades.count(),
        'average': all_grades.aggregate(avg=Avg('valoare'))['avg'] or 0,
        'highest': all_grades.aggregate(max=Max('valoare'))['max'] or 0,
        'lowest': all_grades.aggregate(min=Min('valoare'))['min'] or 0,
    }

    # Distribuția notelor
    grade_distribution = {}
    for i in range(1, 11):
        count = all_grades.filter(valoare__gte=i, valoare__lt=i + 1).count()
        grade_distribution[i] = count

    # Evoluția în timp (ultimele 6 luni)
    months_data = []
    today = date.today()
    for i in range(6):
        month_date = today.replace(day=1) - timedelta(days=30 * i)
        month_grades = all_grades.filter(
            data__year=month_date.year,
            data__month=month_date.month
        )
        avg_grade = month_grades.aggregate(avg=Avg('valoare'))['avg'] or 0
        months_data.append({
            'month': month_date.strftime('%b %Y'),
            'average': round(avg_grade, 2),
            'count': month_grades.count()
        })

    months_data.reverse()

    # Top/bottom materii
    subject_averages = []
    for subject in Subject.objects.filter(user=user, activa=True):
        subject_grades = all_grades.filter(subject=subject)
        if subject_grades.exists():
            avg = subject_grades.aggregate(avg=Avg('valoare'))['avg']
            subject_averages.append({
                'subject': subject,
                'average': round(avg, 2),
                'count': subject_grades.count()
            })

    subject_averages.sort(key=lambda x: x['average'], reverse=True)

    # Absențe
    all_absences = Grade.objects.filter(user=user, tip__in=['absenta', 'absenta_motivata'])
    absence_stats = {
        'total': all_absences.count(),
        'motivated': all_absences.filter(tip='absenta_motivata').count(),
        'unmotivated': all_absences.filter(tip='absenta').count(),
    }

    context = {
        'general_stats': general_stats,
        'grade_distribution': grade_distribution,
        'months_data': months_data,
        'subject_averages': subject_averages,
        'absence_stats': absence_stats,
    }

    return render(request, 'grades/stats.html', context)


@login_required
def grade_calendar_view(request):
    """Calendar cu notele și absențele"""
    user = request.user

    # Obține luna și anul din URL
    month = int(request.GET.get('month', date.today().month))
    year = int(request.GET.get('year', date.today().year))

    # Calculează prima și ultima zi din lună
    from calendar import monthrange
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Notele din această lună
    grades_in_month = Grade.objects.filter(
        user=user,
        data__range=[first_day, last_day]
    ).select_related('subject')

    # Organizează pe zile
    calendar_data = {}
    for grade in grades_in_month:
        day = grade.data.day
        if day not in calendar_data:
            calendar_data[day] = []
        calendar_data[day].append(grade)

    # Navigare
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    context = {
        'calendar_data': calendar_data,
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
        'first_weekday': first_day.weekday(),
    }

    return render(request, 'grades/calendar.html', context)


@login_required
def quick_grade_entry(request):
    """Adăugare rapidă notă - AJAX"""
    if request.method == 'POST':
        try:
            subject_id = request.POST.get('subject_id')
            grade_value = float(request.POST.get('grade_value'))
            grade_type = request.POST.get('grade_type', 'test')
            description = request.POST.get('description', '')

            subject = Subject.objects.get(id=subject_id, user=request.user)

            # Determină semestrul activ
            active_semester = Semester.objects.filter(user=request.user, activ=True).first()
            semester_num = active_semester.numar if active_semester else 1

            grade = Grade.objects.create(
                user=request.user,
                subject=subject,
                tip='nota',
                valoare=grade_value,
                tip_evaluare=grade_type,
                descriere=description,
                semestru=semester_num
            )

            # Actualizează statisticile
            if active_semester:
                stats, created = SubjectGradeStats.objects.get_or_create(
                    user=request.user,
                    subject=subject,
                    semester=active_semester
                )
                stats.calculeaza_statistici()

            return JsonResponse({
                'success': True,
                'grade_id': grade.id,
                'grade_value': float(grade.valoare),
                'subject_name': subject.nume,
                'grade_color': grade.culoare_afisare
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    return JsonResponse({'success': False, 'error': 'Metodă invalidă'})


@login_required
def absence_excuse_view(request, grade_id):
    """Motivează o absență"""
    grade = get_object_or_404(Grade, id=grade_id, user=request.user, tip='absenta')

    if request.method == 'POST':
        grade.motivata = True
        grade.tip = 'absenta_motivata'
        grade.data_motivare = date.today()
        grade.save()

        messages.success(request, 'Absența a fost motivată!')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'new_status': 'motivată'
            })

        return redirect('grades:detail', grade_id=grade.id)

    context = {
        'grade': grade,
    }

    return render(request, 'grades/excuse_absence.html', context)