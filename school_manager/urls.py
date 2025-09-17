"""
URL configuration for school_manager project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.defaults import permission_denied
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),

    # Redirect root to dashboard
    path('', lambda request: redirect('core:dashboard'), name='home'),

    # App URLs
    path('', include('apps.core.urls')),
    path('materii/', include('apps.subjects.urls')),
    path('orar/', include('apps.schedule.urls')),
    path('teme/', include('apps.homework.urls')),
    path('note/', include('apps.grades.urls')),
    # 403 custom fallback (optional explicit path to preview)
    path('403/', permission_denied, {'exception': Exception('Forbidden')}, name='forbidden'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom admin site headers
admin.site.site_header = "School Manager Admin"
admin.site.site_title = "School Manager"
admin.site.index_title = "Administrare aplicație școală"