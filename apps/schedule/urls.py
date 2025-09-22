from django.urls import path
from . import views

app_name = 'schedule'

urlpatterns = [
    # Vedere principală calendar
    path('', views.schedule_calendar_view, name='calendar'),

    # CRUD intrări orar
    path('entry/create/', views.schedule_entry_create_view, name='entry_create'),
    path('entry/<int:entry_id>/edit/', views.schedule_entry_edit_view, name='entry_edit'),
    path('entry/<int:entry_id>/delete/', views.schedule_entry_delete_view, name='entry_delete'),

    # Template-uri orar
    path('templates/', views.schedule_templates_view, name='templates'),
    path('templates/create/', views.schedule_template_create_view, name='template_create'),
    path('templates/<int:template_id>/apply/', views.schedule_template_apply_view, name='template_apply'),
    path('templates/<int:template_id>/delete/', views.schedule_template_delete_view, name='template_delete'),

    # Modificări în orar
    path('changes/', views.schedule_changes_view, name='changes'),
    path('changes/create/', views.schedule_change_create_view, name='change_create'),
    path('changes/<int:change_id>/delete/', views.schedule_change_delete_view, name='change_delete'),

    # Vizualizări speciale
    path('print/', views.schedule_print_view, name='print'),
    path('today/', views.schedule_today_view, name='today'),
    # Export
    path('export/', views.schedule_export_view, name='export'),
    path('year/2025-2026/', views.school_year_2025_2026_view, name='school_year_2025_2026'),

    # AJAX endpoints
    path('quick-edit/', views.schedule_quick_edit_view, name='quick_edit'),

    # Clase și orar pe clasă (admin intern)
    path('classes/', views.classroom_list_view, name='classes'),
    path('classes/create/', views.classroom_create_view, name='class_create'),
    path('classes/<int:class_id>/edit/', views.classroom_edit_view, name='class_edit'),
    path('classes/<int:class_id>/delete/', views.classroom_delete_view, name='class_delete'),
    path('classes/<int:class_id>/schedule/', views.class_schedule_view, name='class_schedule'),
    path('classes/<int:class_id>/schedule/create/', views.class_schedule_entry_create_view, name='class_schedule_entry_create'),
    path('classes/<int:class_id>/schedule/<int:entry_id>/edit/', views.class_schedule_entry_edit_view, name='class_schedule_entry_edit'),
    path('classes/<int:class_id>/schedule/<int:entry_id>/delete/', views.class_schedule_entry_delete_view, name='class_schedule_entry_delete'),
    path('classes/<int:class_id>/schedule/import-from-user/', views.class_schedule_import_from_user, name='class_schedule_import_from_user'),
]