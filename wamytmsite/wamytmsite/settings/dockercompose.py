"""
Django settings for wamytmsite project
for running through docker-compose.yml file.
"""

import os

from . import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = 'DEBUG' in os.environ and os.environ['DEBUG'].upper() in ['TRUE', '1']

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
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'wamytmdb',
        'USER': 'wamytm',
        'PASSWORD': 'Stw9nUvm',
        'HOST': 'db',
        'PORT': '',
    }
}

# Clients > Client ID
SOCIAL_AUTH_KEYCLOAK_KEY = "wamytm"

# Clients > Client > Credentials > Secret
SOCIAL_AUTH_KEYCLOAK_SECRET = "6fd1a212-deed-450c-b28d-3170a0c6102c"

# Realm Settings > Keys > Public key
SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxFXkNZ3uZQ9Zd/GBzkVwbzjhrQ8pJDqLQclUS1XIO34RTA1gRjBVz1d5xWpK9piF0XJGjJGCBPfPQ3cBVEH0xZ+ezpgslZzhh6ur2lv0wugHPwotMXWGIibpO1yiw/wGCszHdroziuwWU9Auf2kOwn1CTjQxg4IOa/fJKyIwxrfppofZNQ3Kq2Z881V9gbXAilDj0Xt8vuO3PEsFghFUce0AFpFtCxX0d8vfxuz92+tUSM/rZf5VR2aXXOdU+sZ3gJwz1w7a4+3eEM9xSD5wJnTbavSjwbJF27Tl4Vngc/tn/Q/5eppDMJb9/STO26OLHXnBUjAZ2PTO0Zau6sU4NQIDAQAB"

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
