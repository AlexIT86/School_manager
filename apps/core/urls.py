from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'core'

urlpatterns = [
    # Autentificare
    path('login/', auth_views.LoginView.as_view(
        template_name='core/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
    path('await-approval/', views.await_approval_view, name='await_approval'),

    # Dashboard și profil
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/setup/', views.profile_setup_view, name='profile_setup'),

    # Notificări
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),

    # Statistici și overview
    path('stats/', views.quick_stats_view, name='quick_stats'),
    path('calendar/', views.calendar_overview, name='calendar_overview'),

    # Role management (superadmin only UI) - evitate coliziuni cu Django Admin
    path('superadmin/roles/', views.roles_overview_view, name='roles_overview'),
    path('superadmin/roles/assign/', views.assign_roles_view, name='assign_roles'),

    # Approvals (superadmin)
    path('superadmin/approvals/', views.approvals_list_view, name='approvals'),
    path('superadmin/approvals/<int:profile_id>/approve/', views.approve_profile_view, name='approve_profile'),

    # Admin users (superadmin)
    path('superadmin/users/', views.admin_users_view, name='admin_users'),
    path('superadmin/users/<int:user_id>/update/', views.admin_user_update_view, name='admin_user_update'),

    # Password reset
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='core/password_reset.html',
        email_template_name='core/password_reset_email.html',
        subject_template_name='core/password_reset_subject.txt'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='core/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='core/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='core/password_reset_complete.html'
    ), name='password_reset_complete'),
]