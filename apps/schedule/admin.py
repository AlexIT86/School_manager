# apps/schedule/admin.py
from django.contrib import admin
from .models import ScheduleEntry, ScheduleTemplate, ScheduleTemplateEntry, ScheduleChange


@admin.register(ScheduleEntry)
class ScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'zi_saptamana', 'numar_ora', 'ora_inceput', 'ora_sfarsit']
    list_filter = ['zi_saptamana', 'tip_ora', 'created_at']
    search_fields = ['user__username', 'subject__nume', 'sala']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Programare', {
            'fields': ('user', 'subject', 'zi_saptamana', 'numar_ora')
        }),
        ('Timp', {
            'fields': ('ora_inceput', 'ora_sfarsit')
        }),
        ('Detalii', {
            'fields': ('sala', 'tip_ora', 'note')
        }),
    )


@admin.register(ScheduleTemplate)
class ScheduleTemplateAdmin(admin.ModelAdmin):
    list_display = ['nume', 'user', 'activ', 'created_at']
    list_filter = ['activ', 'created_at']
    search_fields = ['nume', 'user__username']


@admin.register(ScheduleChange)
class ScheduleChangeAdmin(admin.ModelAdmin):
    list_display = ['schedule_entry', 'tip_schimbare', 'data_start', 'data_end']
    list_filter = ['tip_schimbare', 'data_start']
    search_fields = ['schedule_entry__subject__nume', 'motiv']