"""
Django settings for wamytmsite project
for development.
"""

import os

from . import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '82021938-3cf7-41ac-a314-9af12725f985'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

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
        'HOST': '127.0.0.1',
        'PORT': '',
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
