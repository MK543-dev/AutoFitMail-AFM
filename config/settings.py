"""Django settings for the AutoFitMail (AFM) project."""
import os
from pathlib import Path

import environ
from whitenoise.storage import CompressedManifestStaticFilesStorage


class ManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """WhiteNoise storage that also works before collectstatic has run.

    In production the manifest exists (collectstatic runs at deploy time) and
    files are served hashed; in tests and first local runs it falls back to
    plain URLs instead of raising.
    """

    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content=content, filename=filename)
        except ValueError:
            # Static file not collected yet (tests / fresh checkout).
            return name

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'analyzer',
    'resume_gen',
    'applications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')}
# Keep the SQLite file next to manage.py no matter which directory commands run from.
if DATABASES['default']['ENGINE'].endswith('sqlite3'):
    DATABASES['default']['NAME'] = str(BASE_DIR / 'db.sqlite3')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'config.settings.ManifestStaticFilesStorage'},
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'landing'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email (Gmail SMTP with an app password in production; console backend in DEBUG)
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
# Gmail's alternative to TLS: port 465 with implicit SSL (EMAIL_USE_SSL=True, EMAIL_USE_TLS=False).
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
EMAIL_TIMEOUT = env.int('EMAIL_TIMEOUT', default=30)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
# Google shows app passwords in spaced 4-letter groups; strip spaces so a
# pasted "xxxx xxxx xxxx xxxx" still works.
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='').replace(' ', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'afm@localhost'
_default_email_backend = (
    # Console backend in dev: "sent" emails are printed in the terminal, never really sent.
    'django.core.mail.backends.console.EmailBackend'
    if DEBUG else
    'django.core.mail.backends.smtp.EmailBackend'
)
# EMAIL_BACKEND can be set in .env to override this (e.g. real sends while DEBUG=True).
EMAIL_BACKEND = env('EMAIL_BACKEND', default=_default_email_backend)

# AFM settings
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default='')
# Optional: any Anthropic-Messages-compatible endpoint (e.g. AshnaAI's
# https://api.ashna.ai/v1/api). Empty = Anthropic's own API.
ANTHROPIC_BASE_URL = env('ANTHROPIC_BASE_URL', default='')
if ANTHROPIC_BASE_URL and not os.environ.get('ANTHROPIC_BASE_URL'):
    # The Anthropic SDK reads this environment variable itself, so exporting
    # it is all that is needed to route the writer through a gateway such as
    # AshnaAI (https://api.ashna.ai/v1/api).
    os.environ['ANTHROPIC_BASE_URL'] = ANTHROPIC_BASE_URL
if ANTHROPIC_API_KEY and not os.environ.get('ANTHROPIC_API_KEY'):
    # Same for the key: the SDK reads it from the environment.
    os.environ['ANTHROPIC_API_KEY'] = ANTHROPIC_API_KEY
ANTHROPIC_MODEL = env('ANTHROPIC_MODEL', default='claude-sonnet-4-5')

# AI provider for the resume writer: 'anthropic' (Anthropic or any
# Anthropic-compatible gateway) or 'gemini' (Google AI Studio / Gemini API).
LLM_PROVIDER = env('LLM_PROVIDER', default='anthropic').lower()
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GEMINI_MODEL = env('GEMINI_MODEL', default='gemini-3.8-flash')
GEMINI_BASE_URL = env('GEMINI_BASE_URL', default='https://generativelanguage.googleapis.com/v1beta')
# Skills named in the JD may appear in the tailored resume even when the
# resume itself does not show them (the JD-match the user asked for).
# Set ALLOW_JD_SKILLS=False to require skills to come strictly from the resume.
ALLOW_JD_SKILLS = env.bool('ALLOW_JD_SKILLS', default=True)
DAILY_SEND_LIMIT = env.int('DAILY_SEND_LIMIT', default=20)
MAX_UPLOAD_MB = 5
SKILLS_FILE = BASE_DIR / 'data' / 'skills.json'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Render/Railway terminate TLS in front of the app.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
