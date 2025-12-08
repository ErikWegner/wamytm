"""
Django settings for wamytmsite project
for development.
"""

import os
from . import *
import oracledb
oracledb.init_oracle_client()

TIME_ZONE = 'Europe/Berlin'


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '82021938-3cf7-41ac-a314-9af12725f985'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
#  Oracle
	'default': {
		'ENGINE':   os.environ['WAMYTM_DEV_DB_ENGINE'],
        'NAME':     os.environ['WAMYTM_DEV_DB_NAME'],
        'USER':     os.environ['WAMYTM_DEV_DB_USER'],
        'PASSWORD': os.environ['WAMYTM_DEV_DB_PW'],
        'HOST':     os.environ['WAMYTM_DEV_DB_HOST'],
        'PORT':     os.environ['WAMYTM_DEV_DB_PORT'],
        # Database connection settings for better stability
        'CONN_MAX_AGE': 0,  # Don't reuse connections
        'CONN_HEALTH_CHECKS': True,  # Enable health checks
	},
    'sigapp': {
        'ENGINE':   os.environ['WAMYTM_DEV_DB_ENGINE'],
        'NAME':     os.environ['WAMYTM_DEV_DB_NAME'],
        'USER':     os.environ['WAMYTM_DEV_DB_USER'],
        'PASSWORD': os.environ['WAMYTM_DEV_DB_PW'],
        'HOST':     os.environ['WAMYTM_DEV_DB_HOST'],
        'PORT':     os.environ['WAMYTM_DEV_DB_PORT'],
        # Database connection settings for better stability
        'CONN_MAX_AGE': 0,  # Don't reuse connections
        'CONN_HEALTH_CHECKS': True,  # Enable health checks 
        },
    'imap_app': {
        'ENGINE':   os.environ['WAMYTM_DEV_DB_ENGINE'],
        'NAME':     os.environ['WAMYTM_DEV_DB_NAME'],
        'USER':     os.environ['WAMYTM_DEV_DB_USER'],
        'PASSWORD': os.environ['WAMYTM_DEV_DB_PW'],
        'HOST':     os.environ['WAMYTM_DEV_DB_HOST'],
        'PORT':     os.environ['WAMYTM_DEV_DB_PORT'],
        # Database connection settings for better stability
        'CONN_MAX_AGE': 0,  # Don't reuse connections
        'CONN_HEALTH_CHECKS': True,  # Enable health checks 
        }
}

# Clients > Client ID
SOCIAL_AUTH_KEYCLOAK_KEY = "wamytm"

# Clients > Client > Credentials > Secret
SOCIAL_AUTH_KEYCLOAK_SECRET = "6fd1a212-deed-450c-b28d-3170a0c6102c"

# Realm Settings > Keys > Public key
SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArGuiHOzKTL9l0Djtx/TZxlFQdqLMtxKHn6l0elC4+sE91LlbjqpbiTUDwAPIPEZ9JDFuLwf/fkpr82zN9eXOsqhZ2Sbd6WODWfgmyiNI8Dcq0/H4tSs2CwvWvXo+oPJWKZsOyldaLGUKxk2BzobF8x4NXdZD6GaqebcORYLUL/MJ6FT8DxQaqsXrImBJ1pAov17ExLD9bIKZBxvqAYQn/uvNk8/9u4LUSWEx3sEo+6/a2Ddrg6/tEfb0JIVTjn8PU9Tz0zVw/19flnvm8yAo6BMHJ9ncN2BTtqI7XlIdA4FWeosAeu8y7BAMPv/itP/Pqdx9H1Ep2E48H6DkrExNHQIDAQAB"

SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL = 'https://127.0.0.1:8443/auth/realms/wamytmdev/protocol/openid-connect/auth'
SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = 'https://127.0.0.1:8443/auth/realms/wamytmdev/protocol/openid-connect/token'
SOCIAL_AUTH_KEYCLOAK_ID_KEY = "username"

# Can be set to False for development
VERIFY_SSL = False

# Enable temporary logging (see https://stackoverflow.com/a/51462712)
# LOGGING = { 'version': 1, 'disable_existing_loggers': False, 'handlers': { 'file': { 'level': 'DEBUG', 'class': 'logging.FileHandler', 'filename': '/tmp/debug.log', }, }, 'loggers': { 'django': { 'handlers': ['file'], 'level': 'DEBUG', 'propagate': True, }, }, }
# LOCALE_PATHS = [
#     os.path.join(BASE_DIR, "locale"),
#     os.path.join(BASE_DIR, "wamytmapp/locale"), 
# ]

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
MIDDLEWARE = MIDDLEWARE + ['wamytmsite.settings.dev.DevAutoLoginMiddleware']