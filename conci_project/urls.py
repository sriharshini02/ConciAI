from django.contrib import admin
from django.urls import path, include  # Import include
from django.conf import settings  # For static/media serving in dev
from django.conf.urls.static import static  # For static/media serving in dev

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("main.urls")),  # Include your app's URLs here
]

# Serve static and media files in development (DO NOT USE IN PRODUCTION)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
