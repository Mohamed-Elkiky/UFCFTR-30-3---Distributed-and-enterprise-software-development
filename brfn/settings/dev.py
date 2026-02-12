# brfn/settings/dev.py

from .base import *

DEBUG = True

# For development emails, print to console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'