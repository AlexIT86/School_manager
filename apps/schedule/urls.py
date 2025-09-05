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

    # AJAX endpoints
    path('quick-edit/', views.schedule_quick_edit_view, name='quick_edit'),
]