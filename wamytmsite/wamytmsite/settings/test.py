"""
Django settings for wamytmsite project
for test runs.
"""

from . import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '9dae558a-8521-4124-b525-4730cb3b785e'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
   'default': {
       'ENGINE': 'django.db.backends.sqlite3',
       'NAME': os.path.join(BASE_DIR, 'db-test.sqlite3'),
   }
}

# Clients > Client ID
SOCIAL_AUTH_KEYCLOAK_KEY = "wamytm"

# Clients > Client > Credentials > Secret
SOCIAL_AUTH_KEYCLOAK_SECRET = "435b767e-27c0-42a7-9aac-3606a243fe61"

# Realm Settings > Keys > Public key
SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAgEp4ZxJ5hIEFxUZ4q3EIPsu1H81MdKv/F3phNijPQq9rS8IPTr06Yd/RxlSMvOUk0NYEmcbbHn+4/igXLSLRZcZYcom2c2r3lbkaUCGZy9MtQO1pDVcKMMEKiBl9Xhd1YjhyjTUuzX0C4vJEKwqAq8cz0O42bgdVLHtgz98G7XxsyPpgaUyyYkTqmZw9UNz0QCAervOgYYbdJi3CH6LqX1EcsT7pv3B4XvYNbpjxvMsCUjEUzntMTbpYlbsXYFcpeA6fjbpM/F6xBwWfkK/gC52acV87xbSWjbISJnpaFVM9EOI1Lp4KEiYiv5/0FpdKDdRMZJNTCOTE+UpQGbVfuwIDAQAB"

SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL = 'https://localhost:8443/auth/realms/wamytmdev/protocol/openid-connect/auth'
SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = 'https://localhost:8443/auth/realms/wamytmdev/protocol/openid-connect/token'
SOCIAL_AUTH_KEYCLOAK_ID_KEY = "username"

# Can be set to False for development
VERIFY_SSL = False
