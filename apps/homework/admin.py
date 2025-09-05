# apps/homework/admin.py
from django.contrib import admin
from .models import Homework, HomeworkFile, HomeworkSession, HomeworkReminder


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ['titlu', 'user', 'subject', 'deadline', 'prioritate', 'finalizata', 'progres']
    list_filter = ['finalizata', 'prioritate', 'dificultate', 'deadline', 'created_at']
    search_fields = ['titlu', 'descriere', 'user__username', 'subject__nume']
    readonly_fields = ['created_at', 'updated_at', 'data_finalizare']

    fieldsets = (
        ('Informații de bază', {
            'fields': ('user', 'subject', 'titlu', 'descriere')
        }),
        ('Detalii temă', {
            'fields': ('pagini', 'exercitii', 'data_primita', 'deadline')
        }),
        ('Proprietăți', {
            'fields': ('prioritate', 'dificultate', 'timp_estimat')
        }),
        ('Progress', {
            'fields': ('progres', 'timp_lucrat', 'finalizata', 'data_finalizare')
        }),
        ('Reminder', {
            'fields': ('reminder_activ', 'zile_reminder')
        }),
        ('Note', {
            'fields': ('note_personale', 'dificultati'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HomeworkFile)
class HomeworkFileAdmin(admin.ModelAdmin):
    list_display = ['nume', 'homework', 'tip', 'marime_formatata', 'uploaded_at']
    list_filter = ['tip', 'uploaded_at']
    search_fields = ['nume', 'homework__titlu', 'descriere']


@admin.register(HomeworkSession)
class HomeworkSessionAdmin(admin.ModelAdmin):
    list_display = ['homework', 'inceput', 'sfarsit', 'durata_minute', 'progres_inainte', 'progres_dupa']
    list_filter = ['inceput', 'sfarsit']
    search_fields = ['homework__titlu', 'note_sesiune']
    readonly_fields = ['durata_minute']


@admin.register(HomeworkReminder)
class HomeworkReminderAdmin(admin.ModelAdmin):
    list_display = ['homework', 'data_reminder', 'ora_reminder', 'trimis']
    list_filter = ['trimis', 'data_reminder']
    search_fields = ['homework__titlu', 'mesaj_custom']