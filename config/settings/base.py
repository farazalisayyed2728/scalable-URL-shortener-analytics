import os
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# Path(__file__).resolve().parent.parent.parent targets the project root.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize django-environ
env = environ.Env()

# Read .env file from project root if it exists
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    environ.Env.read_env(env_file)

# Core Security
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
]

# 1. Update LOCAL_APPS to include apps.core
LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.links",
    "apps.analytics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database connection: reads from DATABASE_URL env variable
DATABASES = {
    "default": env.db("DATABASE_URL")
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True  # Strict UTC timezone awareness in database

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework base configuration
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

AUTH_USER_MODEL = "accounts.User"


BASE_DIR = Path(__file__).resolve().parent.parent.parent

AUTH_USER_MODEL = "accounts.User"


BASE_SHORT_URL = env("BASE_SHORT_URL", default="http://localhost:8000")
CODE_LENGTH = env.int("CODE_LENGTH", default=7)
MAX_CODE_RETRIES = env.int("MAX_CODE_RETRIES", default=5)
MAX_URL_LENGTH = env.int("MAX_URL_LENGTH", default=2048)

RESERVED_CODES = {
    "api",
    "admin",
    "docs",
    "static",
    "health",
    "login",
    "register",
    "favicon.ico",
    "robots.txt",
}


# Redis Caching Settings

REDIS_URL = env(
    "REDIS_URL",
    default="redis://127.0.0.1:6379/0"
)

CACHE_TTL_SECONDS = env.int(
    "CACHE_TTL_SECONDS",
    default=86400
)

CACHE_TTL_JITTER_PCT = env.int(
    "CACHE_TTL_JITTER_PCT",
    default=10
)

NEGATIVE_CACHE_TTL_SECONDS = env.int(
    "NEGATIVE_CACHE_TTL_SECONDS",
    default=60
)

NEGATIVE_CACHE_SENTINEL = "__404__"