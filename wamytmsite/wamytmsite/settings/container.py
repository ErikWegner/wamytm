"""
Django settings for wamytmsite project
for running inside a container.

Required settings are available as environment variables.
"""

import os

from . import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = 'WAMYTM_DEBUG' in os.environ and os.environ['WAMYTM_DEBUG'].upper() in ['TRUE', '1']

ALLOWED_HOSTS = ['*']

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {

# SQLite
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#    }

# Postgres
    'default': {
        'ENGINE': os.environ['WAMYTM_DATABASE_ENGINE'],
        'NAME': os.environ['WAMYTM_DATABASE_NAME'],
        'USER': os.environ['WAMYTM_DATABASE_USERNAME'],
        'PASSWORD': os.environ['WAMYTM_DATABASE_PASSWORD'],
        'HOST': os.environ['WAMYTM_DATABASE_HOST'],
        'PORT': os.environ['WAMYTM_DATABASE_PORT'],
    }
}

# Clients > Client ID
SOCIAL_AUTH_KEYCLOAK_KEY = os.environ['WAMYTM_KEYCLOAK_CLIENT_ID']

# Clients > Client > Credentials > Secret
SOCIAL_AUTH_KEYCLOAK_SECRET = os.environ['WAMYTM_KEYCLOAK_CLIENT_SECRET']

# Realm Settings > Keys > Public key
SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY = os.environ['WAMYTM_KEYCLOAK_PUBLIC_KEY']

SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL = os.environ['WAMYTM_KEYCLOAK_AUTH_URL']
SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = os.environ['WAMYTM_KEYCLOAK_TOKEN_URL']
SOCIAL_AUTH_KEYCLOAK_ID_KEY = "username"

# Can be set to False for development
VERIFY_SSL = 'WAMYTM_KEYCLOAK_VERIFY_SSL' not in os.environ or os.environ['WAMYTM_KEYCLOAK_VERIFY_SSL'].upper() in ['TRUE', '1']

# Enable temporary logging (see https://stackoverflow.com/a/51462712)
# LOGGING = { 'version': 1, 'disable_existing_loggers': False, 'handlers': { 'file': { 'level': 'DEBUG', 'class': 'logging.FileHandler', 'filename': '/tmp/debug.log', }, }, 'loggers': { 'django': { 'handlers': ['file'], 'level': 'DEBUG', 'propagate': True, }, }, }
# LOCALE_PATHS = [
#     os.path.join(BASE_DIR, "locale"),
#     os.path.join(BASE_DIR, "wamytmapp/locale"), 
# ]
