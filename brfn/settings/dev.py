# brfn/settings/dev.py

import os

os.environ.setdefault('DATABASE_URL', 'postgresql://myuser:mypassword@localhost:5432/mydb')

from .base import *

DEBUG = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'