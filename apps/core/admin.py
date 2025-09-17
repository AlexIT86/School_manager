# apps/core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import StudentProfile, Notification


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Profile Studenți'
    fk_name = 'user'


class CustomUserAdmin(UserAdmin):
    inlines = (StudentProfileInline,)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'tip', 'titlu', 'citita', 'created_at']
    list_filter = ['tip', 'citita', 'created_at']
    search_fields = ['titlu', 'mesaj', 'user__username']
    readonly_fields = ['created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')