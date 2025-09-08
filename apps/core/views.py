from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import date, timedelta

from .models import StudentProfile, Notification
from .forms import StudentProfileForm, UserRegistrationForm
from apps.subjects.models import Subject
from apps.homework.models import Homework
from apps.grades.models import Grade, SubjectGradeStats
from apps.schedule.models import ScheduleEntry
from django.conf import settings

try:
    from .email_utils import send_email
except Exception:
    send_email = None


def register_view(request):
    """Înregistrare utilizator nou"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Contul pentru {username} a fost creat cu succes!')

            # Trimite email de bun venit (daca este configurat SendGrid)
            if send_email and settings.SENDGRID_API_KEY and user.email:
                try:
                    send_email(
                        to_emails=[user.email],
                        subject='Bun venit în School Manager',
                        html_content=f"""
                        <p>Bun venit, {user.first_name or user.username}!</p>
                        <p>Contul tău a fost creat cu succes. Spor la folosirea aplicației!</p>
                        <p>Cu drag,<br>School Manager</p>
                        """
                    )
                except Exception:
                    pass

            # Autentificare automată
            user = authenticate(username=username, password=form.cleaned_data.get('password1'))
            if user:
                login(request, user)
                return redirect('core:profile_setup')
    else:
        form = UserRegistrationForm()

    return render(request, 'core/register.html', {'form': form})


@login_required
def profile_setup_view(request):
    """Configurare inițială profil student"""
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profilul a fost configurat cu succes!')
            # Email părinte la configurare profil
            if send_email:
                try:
                    refreshed = request.user.student_profile
                    parent_email = getattr(refreshed, 'email_parinte', '')
                    if parent_email:
                        send_email(
                            to_emails=[parent_email],
                            subject='Profil elev configurat',
                            html_content=f"""
                            <p>Bună,</p>
                            <p>Profilul elevului {request.user.get_full_name() or request.user.username} a fost configurat în School Manager.</p>
                            <ul>
                              <li>Clasa: {refreshed.clasa or '-'}</li>
                              <li>Școala: {refreshed.scoala or '-'}</li>
                              <li>Ora de început: {refreshed.ore_start}</li>
                              <li>Reminder teme: {'activ' if refreshed.reminder_teme else 'inactiv'}</li>
                              <li>Reminder note: {'activ' if refreshed.reminder_note else 'inactiv'}</li>
                            </ul>
                            <p>Vă mulțumim!</p>
                            """
                        )
                except Exception:
                    pass
            return redirect('core:dashboard')
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, 'core/profile_setup.html', {'form': form})


@login_required
def dashboard_view(request):
    """Dashboard principal - pagina de start"""
    user = request.user
    today = date.today()

    # Verifică dacă profilul este configurat
    try:
        profile = user.student_profile
        if not profile.clasa:
            return redirect('core:profile_setup')
    except StudentProfile.DoesNotExist:
        return redirect('core:profile_setup')

    # Statistici generale
    total_subjects = Subject.objects.filter(user=user, activa=True).count()

    # Teme urgente (următoarele 3 zile)
    urgent_homework = Homework.objects.filter(
        user=user,
        finalizata=False,
        deadline__lte=today + timedelta(days=3)
    ).order_by('deadline')[:5]

    # Teme de astăzi
    today_homework = Homework.objects.filter(
        user=user,
        finalizata=False,
        deadline=today
    )

    # Note recente (ultimele 7 zile)
    recent_grades = Grade.objects.filter(
        user=user,
        tip='nota',
        data__gte=today - timedelta(days=7)
    ).order_by('-data')[:5]

    # Absențe recente (ultimele 7 zile)
    recent_absences = Grade.objects.filter(
        user=user,
        tip__in=['absenta', 'absenta_motivata'],
        data__gte=today - timedelta(days=7)
    ).order_by('-data')[:3]

    # Orarul de astăzi
    weekday = today.isoweekday()  # 1=Luni, 7=Duminică
    if weekday <= 5:  # Luni-Vineri
        today_schedule = ScheduleEntry.objects.filter(
            user=user,
            zi_saptamana=weekday
        ).order_by('numar_ora')
    else:
        today_schedule = []

    # Notificări necitite
    unread_notifications = Notification.objects.filter(
        user=user,
        citita=False
    ).order_by('-created_at')[:5]

    # Statistici rapide pentru carduri
    # Media luna aceasta (2 zecimale)
    avg_month = Grade.objects.filter(
        user=user,
        tip='nota',
        data__month=today.month,
        data__year=today.year
    ).aggregate(avg=Avg('valoare'))['avg'] or 0
    try:
        avg_month = round(float(avg_month), 2)
    except Exception:
        avg_month = 0

    stats = {
        'total_homework': Homework.objects.filter(user=user, finalizata=False).count(),
        'overdue_homework': Homework.objects.filter(
            user=user,
            finalizata=False,
            deadline__lt=today
        ).count(),
        'total_grades_this_month': Grade.objects.filter(
            user=user,
            tip='nota',
            data__month=today.month,
            data__year=today.year
        ).count(),
        'avg_grade_this_month': avg_month,
    }

    # Media generală
    all_grades = Grade.objects.filter(user=user, tip='nota')
    if all_grades.exists():
        gavg = all_grades.aggregate(avg=Avg('valoare'))['avg'] or 0
        try:
            gavg = round(float(gavg), 2)
        except Exception:
            gavg = 0
        stats['general_average'] = gavg
    else:
        stats['general_average'] = 0

    context = {
        'profile': profile,
        'stats': stats,
        'urgent_homework': urgent_homework,
        'today_homework': today_homework,
        'recent_grades': recent_grades,
        'recent_absences': recent_absences,
        'today_schedule': today_schedule,
        'unread_notifications': unread_notifications,
        'today': today,
        'weekday_name': ['Luni', 'Marți', 'Miercuri', 'Joi', 'Vineri', 'Sâmbătă', 'Duminică'][weekday - 1]
    }

    return render(request, 'core/dashboard.html', context)


@login_required
def profile_view(request):
    """Vizualizare și editare profil"""
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        profile = StudentProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profilul a fost actualizat cu succes!')
            # Email părinte la actualizare profil
            if send_email:
                try:
                    refreshed = request.user.student_profile
                    parent_email = getattr(refreshed, 'email_parinte', '')
                    if parent_email:
                        send_email(
                            to_emails=[parent_email],
                            subject='Profil elev actualizat',
                            html_content=f"""
                            <p>Bună,</p>
                            <p>Profilul elevului {request.user.get_full_name() or request.user.username} a fost actualizat.</p>
                            <ul>
                              <li>Clasa: {refreshed.clasa or '-'}</li>
                              <li>Școala: {refreshed.scoala or '-'}</li>
                              <li>Ora de început: {refreshed.ore_start}</li>
                              <li>Reminder teme: {'activ' if refreshed.reminder_teme else 'inactiv'}</li>
                              <li>Reminder note: {'activ' if refreshed.reminder_note else 'inactiv'}</li>
                            </ul>
                            <p>Vă mulțumim!</p>
                            """
                        )
                except Exception:
                    pass
            return redirect('core:profile')
    else:
        form = StudentProfileForm(instance=profile)

    context = {
        'form': form,
        'profile': profile,
    }

    return render(request, 'core/profile.html', context)


@login_required
def notifications_view(request):
    """Lista tuturor notificărilor"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # Marchează toate ca citite
    notifications.filter(citita=False).update(citita=True)

    context = {
        'notifications': notifications,
    }

    return render(request, 'core/notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Marchează o notificare ca citită"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.citita = True
        notification.save()
    except Notification.DoesNotExist:
        pass

    return redirect('core:notifications')


@login_required
def quick_stats_view(request):
    """Statistici rapide pentru widget-uri"""
    user = request.user
    today = date.today()

    # Calculează statistici pentru fiecare materie
    subjects_stats = []
    for subject in Subject.objects.filter(user=user, activa=True):
        # Note recent
        recent_grades = Grade.objects.filter(
            user=user,
            subject=subject,
            tip='nota',
            data__gte=today - timedelta(days=30)
        )

        # Teme active
        active_homework = Homework.objects.filter(
            user=user,
            subject=subject,
            finalizata=False
        ).count()

        # Media
        avg_grade = recent_grades.aggregate(avg=Avg('valoare'))['avg']

        subjects_stats.append({
            'subject': subject,
            'avg_grade': round(avg_grade, 2) if avg_grade else None,
            'recent_grades_count': recent_grades.count(),
            'active_homework': active_homework,
        })

    context = {
        'subjects_stats': subjects_stats,
    }

    return render(request, 'core/quick_stats.html', context)


@login_required
def calendar_overview(request):
    """Vedere generală calendar cu toate evenimentele"""
    user = request.user
    today = date.today()

    # Evenimente următoarele 30 zile
    events = []

    # Teme
    upcoming_homework = Homework.objects.filter(
        user=user,
        finalizata=False,
        deadline__gte=today,
        deadline__lte=today + timedelta(days=30)
    )

    for hw in upcoming_homework:
        events.append({
            'date': hw.deadline,
            'type': 'homework',
            'title': f"Temă: {hw.titlu}",
            'subject': hw.subject.nume,
            'color': hw.subject.culoare,
            'priority': hw.prioritate,
            'url': f"/teme/{hw.id}/"
        })

    # Testele importante (din note programate)
    # Acest lucru ar putea fi extins cu un model separat pentru teste programate

    # Sortează evenimentele pe dată
    events.sort(key=lambda x: x['date'])

    context = {
        'events': events,
        'today': today,
    }

    return render(request, 'core/calendar_overview.html', context)