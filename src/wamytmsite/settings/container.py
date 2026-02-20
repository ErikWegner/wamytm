from . import *
import oracledb
oracledb.init_oracle_client()

print("wamytmsite.settings.container")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = 'WAMYTM_DEBUG' in os.environ and os.environ['WAMYTM_DEBUG'].upper() in ['TRUE', '1']

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE':   os.environ['DATABASE_ENGINE'],
        'NAME':     os.environ['DATABASE_NAME'],
        'USER':     os.environ['DATABASE_USER'],
        'PASSWORD': os.environ['DATABASE_PASSWORD'],
        'HOST':     os.environ['DATABASE_HOST'],
        'PORT':     os.environ['DATABASE_PORT'],
        # Database connection settings for better stability
        'CONN_MAX_AGE': 0,  # Don't reuse connections
        'CONN_HEALTH_CHECKS': True,  # Enable health checks
    },
    'imap_app': {
        'ENGINE':   os.environ['DATABASE_ENGINE'],
        'NAME':     os.environ['DATABASE_NAME'],
        'USER':     os.environ['DATABASE_USER'],
        'PASSWORD': os.environ['DATABASE_PASSWORD'],
        'HOST':     os.environ['DATABASE_HOST'],
        'PORT':     os.environ['DATABASE_PORT'],
        # Database connection settings for better stability
        'CONN_MAX_AGE': 0,  # Don't reuse connections
        'CONN_HEALTH_CHECKS': True,  # Enable health checks 
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

# Enhanced logging configuration for production debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/tmp/django_warnings.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'wamytmapp': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'imap_app': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

if 'WAMYTM_TRUST_X_FORWARDED_PROTO' in os.environ and os.environ['WAMYTM_TRUST_X_FORWARDED_PROTO'].upper() in ['TRUE', '1']:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

USE_X_FORWARDED_HOST = 'WAMYTM_USE_X_FORWARDED_HOST' in os.environ and os.environ['WAMYTM_USE_X_FORWARDED_HOST'] in ['TRUE', '1']
