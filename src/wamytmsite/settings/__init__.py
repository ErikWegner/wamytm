"""
Django settings for wamytmsite project.
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Application definition

INSTALLED_APPS = [
    'wamytmapp.apps.WamytmappConfig',
    'health_check',                             # required
    'health_check.db',                          # stock Django health checkers
    'bootstrap4',
    'oauth2_provider',
    'social_django',
    'rest_framework_social_oauth2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'simple_history',
    'django_prometheus',
]

# Database Routers
DATABASE_ROUTERS = []

if os.getenv('ENABLE_SIGAPP', 'false').lower() == 'true':
    INSTALLED_APPS.append('sigapp.apps.SigappConfig')
    DATABASE_ROUTERS.append('sigapp.db_router.SigappRouter')

if os.getenv('ENABLE_IMAPAPP', 'false').lower() == 'true':
    INSTALLED_APPS.append('imap_app.apps.ImapAppConfig')
    INSTALLED_APPS.append('django_q')
    INSTALLED_APPS.append('rest_framework.authtoken')  # For API authentication
    DATABASE_ROUTERS.append('imap_app.db_router.IMapAppRouter')

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'wamytmapp.middleware.DatabaseConnectionMiddleware',  # Updated middleware name
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Application definition

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

AUTHENTICATION_BACKENDS = [
    'social_core.backends.keycloak.KeycloakOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',  # For API Token Auth
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        'rest_framework_social_oauth2.authentication.SocialAuthentication',
    ),
}

ROOT_URLCONF = 'wamytmsite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                'imap_app.context_processors.konfiguration_context',
            ],
        },
    },
]

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.social_user',
    #'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'social_core.pipeline.social_auth.associate_by_email',
)

SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['username', 'first_name', 'email']

WSGI_APPLICATION = 'wamytmsite.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'de'

LANGUAGES = [
    ('de', 'Deutsch'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
    # project-level locale directory (e.g. src/locale)
    os.path.join(os.path.dirname(BASE_DIR), 'locale'),
]

TIME_ZONE = 'Europe/Berlin'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'

LOGIN_URL = "/login/keycloak"

# Clients > Client ID
SOCIAL_AUTH_KEYCLOAK_KEY = "wamytm"

# Clients > Client > Credentials > Secret

# Realm Settings > Keys > Public key

SOCIAL_AUTH_KEYCLOAK_ID_KEY = "username"

SIMPLE_HISTORY_REVERT_DISABLED=True

# Can be set to False for development
VERIFY_SSL = True

DRFSO2_PROPRIETARY_BACKEND_NAME = "Keycloak"
DRFSO2_URL_NAMESPACE = "social_core.backends"

# Update to Django 3.2, see https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys
DEFAULT_AUTO_FIELD='django.db.models.AutoField'

# Django Q Configuration
Q_CLUSTER = {
    'name': 'wamytm',
    'workers': 2,  # Reduced for Oracle stability
    'recycle': 50,  # Recycle workers more frequently for Oracle
    'timeout': 300,
    'retry': 360,  # Retry after 360 seconds (must be > timeout)
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q',
    'redis': None,  # Use Django ORM as broker
    'orm': 'default',  # Use default database
    'sync': False,  # Run tasks async
    'catch_up': True,  # Catch up on missed schedules
    'max_attempts': 1,  # Don't retry tasks on Oracle connection errors
    'bulk': 1,  # Process one task at a time for stability
    'guard_cycle': 5,  # Check for new tasks every 5 seconds
    'poll': 0.2,  # Poll interval for pusher
}
