"""wamytmsite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path, re_path
from django.shortcuts import redirect
from django.http import HttpResponse

from wamytmapp.admin import korporator_admin

urlpatterns = [
    path('cal/', include('wamytmapp.urls')),
    path('admin/', admin.site.urls),
    path('ka/', korporator_admin.urls, name="ka"),
    path('', include('social_django.urls', namespace='social')),
    path('', include('django_prometheus.urls')),
    re_path(r'^$', lambda _: redirect('cal/', permanent=False)),
    re_path(r'^status/up$', lambda _: HttpResponse('ok')),
    re_path(r'^status/ht/', include('health_check.urls'))
]
