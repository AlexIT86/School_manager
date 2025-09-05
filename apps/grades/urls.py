from django.urls import path
from . import views

app_name = 'grades'

urlpatterns = [
    # Vedere principală
    path('', views.grades_overview_view, name='overview'),

    # CRUD note și absențe
    path('list/', views.grades_list_view, name='list'),
    path('create/', views.grade_create_view, name='create'),
    path('<int:grade_id>/', views.grade_detail_view, name='detail'),
    path('<int:grade_id>/edit/', views.grade_edit_view, name='edit'),
    path('<int:grade_id>/delete/', views.grade_delete_view, name='delete'),

    # Note pe materii
    path('subject/<int:subject_id>/', views.subject_grades_view, name='subject_grades'),

    # Gestionare semestre
    path('semesters/', views.semesters_view, name='semesters'),
    path('semesters/create/', views.semester_create_view, name='semester_create'),

    # Obiective de note
    path('goals/', views.grade_goals_view, name='goals'),
    path('goals/create/', views.grade_goal_create_view, name='goal_create'),
    path('goals/<int:goal_id>/edit/', views.grade_goal_edit_view, name='goal_edit'),
    path('goals/<int:goal_id>/delete/', views.grade_goal_delete_view, name='goal_delete'),

    # Vizualizări speciale
    path('stats/', views.grades_stats_view, name='stats'),
    path('calendar/', views.grade_calendar_view, name='calendar'),

    # AJAX endpoints
    path('quick-add/', views.quick_grade_entry, name='quick_add'),
    path('<int:grade_id>/excuse/', views.absence_excuse_view, name='excuse_absence'),
]