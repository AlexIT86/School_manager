# apps/subjects/admin.py
from django.contrib import admin
from .models import Subject, SubjectFile, SubjectNote


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['nume', 'user', 'nume_profesor', 'sala', 'activa', 'created_at']
    list_filter = ['activa', 'created_at', 'updated_at']
    search_fields = ['nume', 'nume_profesor', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Informații de bază', {
            'fields': ('user', 'nume', 'nume_profesor', 'sala')
        }),
        ('Aspecte vizuale', {
            'fields': ('culoare',)
        }),
        ('Detalii', {
            'fields': ('descriere', 'manual', 'activa')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SubjectFile)
class SubjectFileAdmin(admin.ModelAdmin):
    list_display = ['nume', 'subject', 'tip', 'marime_formatata', 'uploaded_at']
    list_filter = ['tip', 'uploaded_at']
    search_fields = ['nume', 'subject__nume', 'descriere']
    readonly_fields = ['marime', 'uploaded_at']


@admin.register(SubjectNote)
class SubjectNoteAdmin(admin.ModelAdmin):
    list_display = ['titlu', 'subject', 'important', 'created_at']
    list_filter = ['important', 'created_at', 'updated_at']
    search_fields = ['titlu', 'continut', 'subject__nume']
    readonly_fields = ['created_at', 'updated_at']