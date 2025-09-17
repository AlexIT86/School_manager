from django.shortcuts import render, redirect, get_object_or_404
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
from apps.schedule.models import apply_class_schedule_to_user
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.contrib.sessions.models import Session

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

            # Completează profilul cu școala și clasa selectate; marchează ca neaprobat
            try:
                profile = user.student_profile
            except StudentProfile.DoesNotExist:
                profile = StudentProfile.objects.create(user=user)

            profile.scoala = form.cleaned_data.get('scoala') or ''
            class_room = form.cleaned_data.get('class_room')
            if class_room:
                profile.class_room = class_room
                # Setează și câmpul text "clasa" din numele clasei
                if not profile.clasa:
                    profile.clasa = class_room.nume

            profile.approved = False
            profile.save()

            messages.success(request, f'Contul pentru {username} a fost creat. Așteaptă aprobarea administratorului.')

            # Trimite email de bun venit (daca este configurat SendGrid)
            if send_email and settings.SENDGRID_API_KEY and user.email:
                try:
                    send_email(
                        to_emails=[user.email],
                        subject='Cont creat - în așteptarea aprobării',
                        html_content=f"""
                        <p>Bun venit, {user.first_name or user.username}!</p>
                        <p>Contul tău a fost creat și este în așteptarea aprobării de către un administrator.</p>
                        <p>Vei primi acces la orar și toate funcționalitățile imediat după aprobare.</p>
                        <p>Cu drag,<br>School Manager</p>
                        """
                    )
                except Exception:
                    pass

            # Autentificare automată și redirect la pagina de așteptare aprobare
            user = authenticate(username=username, password=form.cleaned_data.get('password1'))
            if user:
                login(request, user)
                return redirect('core:await_approval')
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
            profile = form.save()
            messages.success(request, 'Profilul a fost configurat cu succes!')
            # Dacă s-a selectat o clasă globală și elevul nu are orar încă, copiază orarul clasei
            try:
                if getattr(profile, 'class_room', None):
                    created_count = apply_class_schedule_to_user(profile.class_room, request.user)
                    if created_count > 0:
                        messages.success(request, f'Orarul clasei {profile.class_room.nume} a fost preluat ({created_count} ore).')
            except Exception:
                pass
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
def await_approval_view(request):
    """Pagină de așteptare până la aprobarea contului de către administrator."""
    try:
        profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        return redirect('core:profile_setup')

    # Dacă a fost aprobat între timp, du-l în dashboard
    if getattr(profile, 'approved', False):
        return redirect('core:dashboard')

    return render(request, 'core/await_approval.html', { 'profile': profile })


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

    # Dacă nu este aprobat încă, redirecționează la pagina de așteptare
    if not getattr(profile, 'approved', True):
        return redirect('core:await_approval')

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

    # --- Module progress (2025–2026) și următoarea vacanță (ajustat după județ) ---
    # Județul elevului (dacă are clasă asociată)
    judet = None
    try:
        if profile and getattr(profile, 'class_room', None) and profile.class_room.judet:
            judet = profile.class_room.judet.strip()
    except Exception:
        pass

    grupa1 = {'Cluj', 'Timiș', 'Bistrița-Năsăud'}  # 9-15 feb
    grupa2 = {
        'București', 'Ilfov', 'Sălaj', 'Bihor', 'Arad', 'Iași', 'Hunedoara', 'Brașov',
        'Caraș-Severin', 'Gorj', 'Vâlcea', 'Argeș', 'Dâmbovița', 'Prahova', 'Buzău',
        'Tulcea', 'Mehedinți', 'Dolj', 'Olt', 'Teleorman', 'Ialomița', 'Călărași'
    }  # 16-22 feb
    grupa3 = {
        'Satu-Mare', 'Maramureș', 'Suceava', 'Botoșani', 'Alba', 'Sibiu', 'Mureș',
        'Harghita', 'Neamț', 'Covasna', 'Bacău', 'Vrancea', 'Vaslui', 'Galați',
        'Brăila', 'Giurgiu', 'Constanța'
    }  # 23 feb - 1 mar

    end_m3 = date(2026, 2, 13)
    start_m4 = date(2026, 2, 23)
    if judet in grupa1:
        end_m3 = date(2026, 2, 6)
        start_m4 = date(2026, 2, 16)
    elif judet in grupa3:
        end_m3 = date(2026, 2, 20)
        start_m4 = date(2026, 3, 2)

    modules = [
        (1, date(2025, 9, 8),  date(2025, 10, 24)),
        (2, date(2025, 11, 3), date(2025, 12, 19)),
        (3, date(2026, 1, 8),  end_m3),
        (4, start_m4,          date(2026, 4, 3)),
        (5, date(2026, 4, 15), date(2026, 6, 19)),
    ]

    current_module = None
    for mnum, mstart, mend in modules:
        if mstart <= today <= mend:
            current_module = (mnum, mstart, mend)
            break

    module_progress = None
    if current_module:
        mnum, mstart, mend = current_module
        total_days = max(1, (mend - mstart).days)
        passed_days = max(0, (today - mstart).days)
        percent = min(100, max(0, int(round(passed_days * 100 / total_days))))
        module_progress = {
            'number': mnum,
            'start': mstart,
            'end': mend,
            'percent': percent,
            'days_passed': passed_days,
            'days_total': total_days,
        }

    # Vacanțe (următoarea)
    vac_feb_start = date(2026, 2, 9) if judet in grupa1 else (date(2026, 2, 16) if judet in grupa2 else (date(2026, 2, 23) if judet in grupa3 else date(2026, 2, 16)))
    vac_feb_end = date(2026, 2, 15) if judet in grupa1 else (date(2026, 2, 22) if judet in grupa2 else (date(2026, 3, 1) if judet in grupa3 else date(2026, 2, 22)))
    vacations = [
        ('Vacanța de toamnă', date(2025, 10, 25), date(2025, 11, 2)),
        ('Vacanța de iarnă', date(2025, 12, 20), date(2026, 1, 7)),
        ('Vacanța mobilă din februarie', vac_feb_start, vac_feb_end),
        ('Vacanța de primăvară', date(2026, 4, 4), date(2026, 4, 14)),
        ('Vacanța de vară', date(2026, 6, 20), date(2026, 9, 6)),
    ]
    next_vacation = None
    for vname, vstart, vend in vacations:
        if vstart > today:
            next_vacation = {'name': vname, 'start': vstart}
            break

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
        'weekday_name': ['Luni', 'Marți', 'Miercuri', 'Joi', 'Vineri', 'Sâmbătă', 'Duminică'][weekday - 1],
        'module_progress': module_progress,
        'next_vacation': next_vacation,
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
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Handle remove image
            if form.cleaned_data.get('remove_image'):
                try:
                    if profile.profile_image:
                        profile.profile_image.delete(save=False)
                    profile.profile_image = None
                except Exception:
                    pass

            profile = form.save()

            # Post-procesare poză: rotire / decupare / redimensionare
            rotate_deg = 0
            try:
                rotate_deg = int(form.cleaned_data.get('rotate_deg') or 0)
            except Exception:
                rotate_deg = 0
            crop_square = bool(form.cleaned_data.get('crop_square') or False)

            try:
                if profile.profile_image and (rotate_deg or crop_square):
                    from PIL import Image
                    img_path = profile.profile_image.path
                    with Image.open(img_path) as im:
                        # Rotire (sens orar): Pillow folosește unghi anti-orar, deci -deg
                        if rotate_deg in (90, 180, 270):
                            im = im.rotate(-rotate_deg, expand=True)
                        # Decupare pătrată din centru
                        if crop_square:
                            w, h = im.size
                            side = min(w, h)
                            left = (w - side) // 2
                            top = (h - side) // 2
                            im = im.crop((left, top, left + side, top + side))
                        # Redimensionare la 256x256 (pentru avatar clar)
                        im = im.convert('RGB')
                        im = im.resize((256, 256))
                        # Salvează peste fișierul existent
                        im.save(img_path, quality=92)
            except Exception:
                # Ignoră problemele cu procesarea imaginii, dar continuă salvarea profilului
                pass

            messages.success(request, 'Profilul a fost actualizat cu succes!')
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


@login_required
def roles_overview_view(request):
    """UI simplă pentru administrarea rolurilor și permisiunilor (doar superadmin)."""
    if not request.user.is_superuser:
        raise PermissionDenied

    # Asigură existența grupurilor implicite
    for name in ['Elev', 'Părinte', 'Diriginte', 'Superadmin']:
        Group.objects.get_or_create(name=name)

    groups = Group.objects.all().order_by('name')
    users = User.objects.all().order_by('username')

    # Grupare permisiuni pe "meniuri" (aplicații principale din navbar)
    menu_to_apps = {
        'Dashboard/Core': ['core'],
        'Materii': ['subjects'],
        'Orar': ['schedule'],
        'Teme': ['homework'],
        'Note': ['grades'],
    }

    grouped_permissions = []
    for menu_name, app_labels in menu_to_apps.items():
        perms = Permission.objects.filter(content_type__app_label__in=app_labels).order_by('content_type__model', 'codename')
        grouped_permissions.append({
            'menu': menu_name,
            'app_labels': app_labels,
            'permissions': perms,
        })

    # Selectează grupul curent
    selected_group_id = request.GET.get('group')
    try:
        selected_group = Group.objects.get(id=int(selected_group_id)) if selected_group_id else groups.first()
    except Exception:
        selected_group = groups.first()

    assigned_perm_ids = set()
    if selected_group:
        assigned_perm_ids = set(selected_group.permissions.values_list('id', flat=True))

    context = {
        'groups': groups,
        'users': users,
        'grouped_permissions': grouped_permissions,
        'selected_group': selected_group,
        'assigned_perm_ids': assigned_perm_ids,
    }
    return render(request, 'core/roles_overview.html', context)


@login_required
def approvals_list_view(request):
    """Listă cu utilizatori în așteptare de aprobare (doar superadmin)."""
    if not request.user.is_superuser:
        raise PermissionDenied

    pending_profiles = StudentProfile.objects.filter(approved=False).select_related('user', 'class_room').order_by('created_at')

    context = {
        'pending_profiles': pending_profiles,
    }
    return render(request, 'core/approvals.html', context)


@login_required
def approve_profile_view(request, profile_id):
    """Aprobă un profil și preia orarul clasei pentru utilizatorul respectiv (doar superadmin)."""
    if not request.user.is_superuser:
        raise PermissionDenied

    try:
        profile = StudentProfile.objects.select_related('user', 'class_room').get(id=profile_id)
    except StudentProfile.DoesNotExist:
        messages.error(request, 'Profilul selectat nu există.')
        return redirect('core:approvals')

    if request.method != 'POST':
        return redirect('core:approvals')

    profile.approved = True
    profile.approved_at = timezone.now()
    profile.approved_by = request.user

    # Asigură setarea "clasa" text și preia orarul clasei, dacă este definită
    if profile.class_room and not profile.clasa:
        profile.clasa = profile.class_room.nume
    profile.save()

    created_count = 0
    try:
        if profile.class_room:
            created_count = apply_class_schedule_to_user(profile.class_room, profile.user)
    except Exception:
        created_count = 0

    messages.success(request, f'Profilul pentru {profile.user.username} a fost aprobat. Orar preluat: {created_count} intrări.')
    return redirect('core:approvals')


@login_required
def admin_users_view(request):
    """Superadmin: statistici utilizatori (online/total) și CRUD de bază."""
    if not request.user.is_superuser:
        raise PermissionDenied

    # Utilizatori online pe baza sesiunilor active
    try:
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        user_ids_online = set()
        for s in active_sessions:
            try:
                data = s.get_decoded()
                uid = int(data.get('_auth_user_id')) if data.get('_auth_user_id') else None
                if uid:
                    user_ids_online.add(uid)
            except Exception:
                continue
    except Exception:
        user_ids_online = set()

    # Listare utilizatori cu stat
    users = User.objects.all().order_by('-is_superuser', '-is_staff', '-is_active', '-date_joined')

    # Filtre opționale
    q = request.GET.get('q', '').strip()
    if q:
        users = users.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))

    total_users = User.objects.count()
    online_count = users.filter(id__in=user_ids_online).count() if user_ids_online else 0

    context = {
        'users': users,
        'total_users': total_users,
        'online_count': online_count,
        'user_ids_online': user_ids_online,
        'q': q,
    }

    return render(request, 'core/admin_users.html', context)


@login_required
def admin_user_update_view(request, user_id):
    """Superadmin: acțiuni pe utilizator (activare/dezactivare, email, parolă)."""
    if not request.user.is_superuser:
        raise PermissionDenied

    target_user = get_object_or_404(User, id=user_id)

    if request.method != 'POST':
        return redirect('core:admin_users')

    action = request.POST.get('action')
    try:
        if action == 'activate':
            target_user.is_active = True
            target_user.save(update_fields=['is_active'])
            messages.success(request, f'Utilizatorul {target_user.username} a fost activat.')
        elif action == 'deactivate':
            target_user.is_active = False
            target_user.save(update_fields=['is_active'])
            messages.success(request, f'Utilizatorul {target_user.username} a fost dezactivat.')
        elif action == 'set_email':
            new_email = (request.POST.get('email') or '').strip()
            target_user.email = new_email
            target_user.save(update_fields=['email'])
            messages.success(request, f'Email actualizat pentru {target_user.username}.')
        elif action == 'set_password':
            new_password = (request.POST.get('password') or '').strip()
            if not new_password:
                messages.error(request, 'Parola nu poate fi goală.')
            else:
                target_user.set_password(new_password)
                target_user.save()
                messages.success(request, f'Parola a fost schimbată pentru {target_user.username}.')
        else:
            messages.error(request, 'Acțiune necunoscută.')
    except Exception:
        messages.error(request, 'Operația a eșuat.')

    return redirect('core:admin_users')


@login_required
def assign_roles_view(request):
    """Punct de post pentru asignarea/actualizarea rolurilor (doar superadmin)."""
    if not request.method == 'POST':
        return redirect('core:roles_overview')
    if not request.user.is_superuser:
        raise PermissionDenied

    try:
        action = request.POST.get('action')
        if action == 'add_user_to_group':
            user_id = int(request.POST.get('user_id'))
            group_id = int(request.POST.get('group_id'))
            user = User.objects.get(id=user_id)
            group = Group.objects.get(id=group_id)
            group.user_set.add(user)
            messages.success(request, f'Utilizatorul {user.username} a fost adăugat în grupul {group.name}.')
        elif action == 'remove_user_from_group':
            user_id = int(request.POST.get('user_id'))
            group_id = int(request.POST.get('group_id'))
            user = User.objects.get(id=user_id)
            group = Group.objects.get(id=group_id)
            group.user_set.remove(user)
            messages.success(request, f'Utilizatorul {user.username} a fost eliminat din grupul {group.name}.')
        elif action == 'add_permission_to_group':
            group_id = int(request.POST.get('group_id'))
            perm_id = int(request.POST.get('permission_id'))
            group = Group.objects.get(id=group_id)
            perm = Permission.objects.get(id=perm_id)
            group.permissions.add(perm)
            messages.success(request, f'Permisiunea {perm.codename} a fost adăugată grupului {group.name}.')
        elif action == 'remove_permission_from_group':
            group_id = int(request.POST.get('group_id'))
            perm_id = int(request.POST.get('permission_id'))
            group = Group.objects.get(id=group_id)
            perm = Permission.objects.get(id=perm_id)
            group.permissions.remove(perm)
            messages.success(request, f'Permisiunea {perm.codename} a fost eliminată din grupul {group.name}.')
        elif action == 'update_group_permissions':
            group_id = int(request.POST.get('group_id'))
            group = Group.objects.get(id=group_id)
            perm_ids = request.POST.getlist('perm_ids')
            # Înlocuiește setul de permisiuni cu cele selectate
            new_perms = Permission.objects.filter(id__in=[int(pid) for pid in perm_ids])
            group.permissions.set(new_perms)
            messages.success(request, f'Permisiunile pentru {group.name} au fost actualizate.')
    except Exception:
        messages.error(request, 'Operația a eșuat. Verifică datele trimise.')

    # Redirecționează înapoi păstrând grupul selectat
    redirect_group = request.POST.get('group_id')
    return redirect(f"{reverse('core:roles_overview')}?group={redirect_group}")