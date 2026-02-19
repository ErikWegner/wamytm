from django.contrib import admin
from django.urls import include, path, re_path
from django.shortcuts import redirect
from django.http import HttpResponse
from health_check.views import HealthCheckView
import os
    
from wamytmapp.admin import korporator_admin

urlpatterns = [
    path('cal/', include('wamytmapp.urls')),
    path('admin/', admin.site.urls),
    path('ka/', korporator_admin.urls, name="ka"),
    path('', include('social_django.urls', namespace='social')),
    path('', include('django_prometheus.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    re_path(r'^$', lambda _: redirect('cal/', permanent=False)),
    re_path(r'^status/up$', lambda _: HttpResponse('ok')),
    path('status/ht/', HealthCheckView.as_view(
        checks=[
            "health_check.Cache",
            "health_check.Database"
        ])),
]

# Bedingte Einbindung der imap_app URLs
if os.getenv('ENABLE_IMAPAPP', 'false').lower() == 'true':
    print("Adding imap_app URLs")
    urlpatterns += [
        path('ewosa/', include('imap_app.urls')),
    ]
