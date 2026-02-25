# brfn/settings/dev.py

from .base import *
import os

DEBUG = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/brfn')