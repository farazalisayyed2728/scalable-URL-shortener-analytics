import os
from datetime import timedelta
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
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
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
    "apps.core.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.AccessLogMiddleware",
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

DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=600)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # Verify connection is valid before reuse

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

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Pagination
PAGE_SIZE_DEFAULT = env.int("PAGE_SIZE_DEFAULT", default=20)
PAGE_SIZE_MAX = env.int("PAGE_SIZE_MAX", default=100)

# Django REST Framework base configuration
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": PAGE_SIZE_DEFAULT,
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}


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


# In config/settings/base.py:

# Rate Limiting Configuration
RATE_LIMIT_CREATE_PER_MIN = env.int("RATE_LIMIT_CREATE_PER_MIN", default=100)
RATE_LIMIT_FAIL_OPEN = env.bool("RATE_LIMIT_FAIL_OPEN", default=True)

# Reverse Proxy Security
# Set to 1 if behind 1 trusted reverse proxy (e.g., Nginx, AWS ALB, Cloudflare)
# Set to 0 if running directly exposed (e.g., local development without proxy)
NUM_PROXIES = env.int("NUM_PROXIES", default=0)


# -------------------------------------------------------------
# Celery Configuration
# -------------------------------------------------------------
# Broker: Redis Database 1 (Decoupled from Cache on DB 0)
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/1")

# We do not need to store task return values for analytics click ingestion
CELERY_RESULT_BACKEND = None
CELERY_IGNORE_RESULT = True

# Message Serialization: Strict JSON
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Reliability & Concurrency Invariants
# 1. Late Acknowledgement: ack task ONLY after execution completes without crash
CELERY_TASK_ACKS_LATE = True

# 2. Fair Dispatching: Worker pulls only 1 task at a time instead of hoarding 4.
# Prevents head-of-line blocking if one task takes longer than others.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# 3. Connection retry on startup
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

BLOCK_PRIVATE_IPS = env.bool("BLOCK_PRIVATE_IPS", default=True)

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)

CORS_ALLOW_CREDENTIALS = True

# 5. Baseline Security Headers
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"


#Comprehensive Structured Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "apps.core.logging.RequestIDFilter",
        },
    },
    "formatters": {
        "json": {
            "()": "apps.core.logging.JSONLogFormatter",
        },
        "simple": {
            "format": "[{asctime}] {levelname} [{name}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_id"],
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "access": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

SPECTACULAR_SETTINGS = {
    "OAS_VERSION": "3.0.3",
    "TITLE": "ShortLink Scalable Backend API",
    "DESCRIPTION": (
        "High-performance, production-grade URL shortening and real-time analytics backend.\n\n"
        "Features Redis cache-aside resolution, atomic rate limiting, concurrency protection, "
        "asynchronous telemetry ingestion via Celery, and comprehensive observability."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {
            "name": "Authentication",
            "description": "User registration and JWT token management.",
        },
        {
            "name": "URLs",
            "description": "Create, list, retrieve, update, and delete short URLs.",
        },
        {
            "name": "Analytics",
            "description": "Click analytics and reporting for short URLs.",
        },
        {
            "name": "Redirect",
            "description": "Resolve short codes to their original destinations.",
        },
    ],
    # Configure JWT Bearer authorization in Swagger UI
    "SECURITY": [{"BearerAuth": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter your JWT Access Token (e.g. from /api/auth/login/).",
            }
        }
    },
}