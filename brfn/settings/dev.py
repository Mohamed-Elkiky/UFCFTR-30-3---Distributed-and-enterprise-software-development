from .base import *

DEBUG = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DJANGO_DB_NAME", "mydb"),
        "USER": os.environ.get("DJANGO_DB_USER", "myuser"),
        "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", "mypassword"),
        "HOST": os.environ.get("DJANGO_DB_HOST", "db"),
        "PORT": os.environ.get("DJANGO_DB_PORT", "5432"),
    }
}