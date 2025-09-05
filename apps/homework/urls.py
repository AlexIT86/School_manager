from django.urls import path
from . import views

app_name = 'homework'

urlpatterns = [
    # Lista și CRUD teme
    path('', views.homework_list_view, name='list'),
    path('create/', views.homework_create_view, name='create'),
    path('<int:homework_id>/', views.homework_detail_view, name='detail'),
    path('<int:homework_id>/edit/', views.homework_edit_view, name='edit'),
    path('<int:homework_id>/delete/', views.homework_delete_view, name='delete'),

    # Acțiuni pe teme
    path('<int:homework_id>/toggle-complete/', views.homework_complete_toggle, name='toggle_complete'),
    path('<int:homework_id>/update-progress/', views.homework_update_progress, name='update_progress'),

    # Fișiere
    path('<int:homework_id>/files/upload/', views.homework_file_upload_view, name='file_upload'),
    path('<int:homework_id>/files/<int:file_id>/delete/', views.homework_file_delete_view, name='file_delete'),

    # Sesiuni de lucru
    path('<int:homework_id>/session/start/', views.homework_session_start, name='session_start'),
    path('<int:homework_id>/session/<int:session_id>/end/', views.homework_session_end, name='session_end'),

    # Vizualizări speciale
    path('calendar/', views.homework_calendar_view, name='calendar'),
    path('stats/', views.homework_stats_view, name='stats'),
]