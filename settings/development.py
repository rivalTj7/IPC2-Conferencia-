from .base import *

DEBUG = True
SECRET_KEY = 'django-insecure-development-key-for-sigte-project'
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'