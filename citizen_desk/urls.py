"""
URL configuration for citizen_desk project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('desk.urls')),  # All CitizenDesk URLs will be in the desk app
]

# Serve media files during development (user uploaded images)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
