"""
Django settings for wamytmsite project
for running container builds.
"""

from . import *

TIME_ZONE = 'Europe/Berlin'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "1"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

DATABASES = { }
