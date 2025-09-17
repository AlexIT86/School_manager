from django.urls import path
from . import views

app_name = 'subjects'

urlpatterns = [
    # Lista și CRUD materii
    path('', views.subject_list_view, name='list'),
    path('create/', views.subject_create_view, name='create'),
    path('<int:subject_id>/', views.subject_detail_view, name='detail'),
    path('<int:subject_id>/edit/', views.subject_edit_view, name='edit'),
    path('<int:subject_id>/delete/', views.subject_delete_view, name='delete'),

    # Rating
    path('<int:subject_id>/rating/<int:value>/', views.subject_set_rating_view, name='set_rating'),
    path('<int:subject_id>/set-color/', views.subject_set_color_view, name='set_color'),

    # Fișiere
    path('<int:subject_id>/files/', views.subject_files_view, name='files'),
    path('<int:subject_id>/files/upload/', views.subject_file_upload_view, name='file_upload'),
    path('<int:subject_id>/files/<int:file_id>/delete/', views.subject_file_delete_view, name='file_delete'),
    path('<int:subject_id>/files/<int:file_id>/download/', views.download_subject_file, name='file_download'),

    # Notițe
    path('<int:subject_id>/notes/', views.subject_notes_view, name='notes'),
    path('<int:subject_id>/notes/create/', views.subject_note_create_view, name='note_create'),
    path('<int:subject_id>/notes/<int:note_id>/edit/', views.subject_note_edit_view, name='note_edit'),
    path('<int:subject_id>/notes/<int:note_id>/delete/', views.subject_note_delete_view, name='note_delete'),

    # Statistici
    path('<int:subject_id>/stats/', views.subject_stats_view, name='stats'),
]