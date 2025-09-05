# apps/grades/admin.py
from django.contrib import admin
from .models import Grade, Semester, SubjectGradeStats, GradeGoal


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'tip', 'valoare', 'data', 'semestru']
    list_filter = ['tip', 'semestru', 'data', 'importante']
    search_fields = ['user__username', 'subject__nume', 'descriere']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Informații de bază', {
            'fields': ('user', 'subject', 'tip', 'valoare')
        }),
        ('Detalii evaluare', {
            'fields': ('tip_evaluare', 'descriere', 'data', 'semestru')
        }),
        ('Pentru absențe', {
            'fields': ('motivata', 'data_motivare'),
            'classes': ('collapse',)
        }),
        ('Note', {
            'fields': ('note_personale', 'importante')
        }),
    )


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ['user', 'numar', 'an_scolar', 'data_inceput', 'data_sfarsit', 'activ']
    list_filter = ['numar', 'an_scolar', 'activ']
    search_fields = ['user__username', 'an_scolar']


@admin.register(SubjectGradeStats)
class SubjectGradeStatsAdmin(admin.ModelAdmin):
    list_display = ['subject', 'semester', 'media', 'numar_note', 'numar_absente', 'tendinta']
    list_filter = ['semester', 'tendinta', 'updated_at']
    search_fields = ['subject__nume', 'user__username']
    readonly_fields = ['updated_at']


@admin.register(GradeGoal)
class GradeGoalAdmin(admin.ModelAdmin):
    list_display = ['subject', 'semester', 'media_dorita', 'atins', 'data_atins']
    list_filter = ['atins', 'semester', 'created_at']
    search_fields = ['subject__nume', 'user__username']