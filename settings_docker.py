"""
Docker-specific Django settings for story_django project.
Extends the base settings with Docker-friendly configurations.
"""

import os
from pathlib import Path
from story_django.settings import *

# Security - Use environment variable or keep the generated one from entrypoint
SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)

# Allow all hosts for Docker deployment (you can restrict this if needed)
ALLOWED_HOSTS = ['*']

# Debug - Default to False in Docker, can be overridden
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Database - Keep SQLite but point to persistent volume
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': Path('/app/data/db.sqlite3'),
    }
}

# Static files - Configure for whitenoise
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# Add whitenoise to serve static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Whitenoise settings for compression and caching
WHITENOISE_COMPRESS_OFFLINE = True
WHITENOISE_AUTOREFRESH = DEBUG

# Media files - Point to persistent volume
MEDIA_URL = '/media/'
MEDIA_ROOT = Path('/app/data/media')

# API Keys - Allow environment variables to override
OPENAI_KEY = os.environ.get('OPENAI_KEY', '')
GOOGLE_API = os.environ.get('GOOGLE_API', '')
STABILITY_API_KEY = os.environ.get('STABILITY_API_KEY', '')
FAL_KEY = os.environ.get('FAL_KEY', '')

# CSRF settings for proxy deployments
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:8000,http://127.0.0.1:8000'
).split(',')

# Security headers for production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False').lower() == 'true'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

print(f"Docker settings loaded. Debug: {DEBUG}, Database: {DATABASES['default']['NAME']}")