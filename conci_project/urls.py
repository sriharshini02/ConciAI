# conci_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')), # Django's built-in auth URLs

    # Redirect root to login page
    path('', RedirectView.as_view(url='/login/', permanent=True)), 

    # Django's built-in login/logout views (as you defined them)
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'),
    
    # IMPORTANT: Include your main app's URLs here!
    # This will make all paths defined in main/urls.py accessible.
    # Since your main.urls has paths like 'dashboard/', 'guest/', 'api/', etc.,
    # including it at the root '' will make them accessible at /dashboard/, /guest/, /api/
    path('', include('main.urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

