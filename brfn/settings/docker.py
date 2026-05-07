# brfn/settings/docker.py

import os
from .base import *

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

# Allow connections from Docker services and localhost
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'web', 'nginx']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DJANGO_DB_NAME', 'brfn'),
        'USER': os.environ.get('DJANGO_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DJANGO_DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DJANGO_DB_HOST', 'db'),
        'PORT': os.environ.get('DJANGO_DB_PORT', '5432'),
    }
}

# Static files collected here for nginx to serve
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')