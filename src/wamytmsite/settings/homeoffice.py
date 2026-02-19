from . import *

print("wamytmsite.settings.homeoffice")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '82021938-3cf7-41ac-a314-9af12725f985'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

# Use SQLite for development in this environment
try:
    db_file = BASE_DIR / 'db.sqlite3'
except Exception:
    # Fallback if BASE_DIR is a str or not defined as Path
    if 'BASE_DIR' in globals():
        db_file = os.path.join(BASE_DIR, 'db.sqlite3')
    else:
        # Fallback to a path relative to this file
        db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'db.sqlite3')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(db_file),
    },
    'sigapp': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(db_file),
    },
    'imap_app': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(db_file),
    },
}

# Can be set to False for development
VERIFY_SSL = False

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Development-spezifisches Auto-Login
class DevAutoLoginMiddleware:
    """
    Middleware für automatisches Einloggen in der Entwicklungsumgebung
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Auto-Login nur wenn nicht bereits eingeloggt
        if not request.user.is_authenticated:
            from django.contrib.auth.models import User
            from django.contrib.auth import login
            try:
                # Hier können Sie die User-ID anpassen
                user = User.objects.get(id=152)
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
            except User.DoesNotExist:
                pass  # User existiert nicht, nichts tun
        
        response = self.get_response(request)
        return response

# Middleware zur Liste hinzufügen (nur in dev)
MIDDLEWARE = MIDDLEWARE + ['wamytmsite.settings.homeoffice.DevAutoLoginMiddleware']