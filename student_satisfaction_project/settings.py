# student_satisfaction_project/settings.py
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


# V17.1 — configuration environnement / production
def _env_bool(name, default=False):
    raw = os.environ.get(name)

    if raw is None:
        return bool(default)

    return raw.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _env_int(name, default):
    raw = os.environ.get(name)

    if raw is None or not raw.strip():
        return int(default)

    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"{name} doit être un entier."
        ) from exc


def _env_csv(name, default=""):
    return [
        item.strip()
        for item in os.environ.get(name, default).split(",")
        if item.strip()
    ]


ENVIRONMENT = os.environ.get(
    "DJANGO_ENV",
    "development",
).strip().lower()

IS_PRODUCTION = ENVIRONMENT == "production"

if ENVIRONMENT not in {"development", "test", "production"}:
    raise ImproperlyConfigured(
        "DJANGO_ENV doit valoir development, test ou production."
    )


SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "",
).strip()

if not SECRET_KEY:
    if IS_PRODUCTION:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY est obligatoire en production."
        )

    SECRET_KEY = (
        "django-insecure-local-development-only-change-me"
    )


DEBUG = _env_bool(
    "DJANGO_DEBUG",
    default=not IS_PRODUCTION,
)

if IS_PRODUCTION and DEBUG:
    raise ImproperlyConfigured(
        "DJANGO_DEBUG doit être désactivé en production."
    )


ALLOWED_HOSTS = _env_csv(
    "DJANGO_ALLOWED_HOSTS",
    default=(
        ""
        if IS_PRODUCTION
        else "localhost,127.0.0.1,[::1]"
    ),
)

if IS_PRODUCTION:
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS est obligatoire en production."
        )

    if "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS='*' est refusé en production."
        )


CSRF_TRUSTED_ORIGINS = _env_csv(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
)

if IS_PRODUCTION and not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured(
        "DJANGO_CSRF_TRUSTED_ORIGINS est obligatoire en production."
    )

if IS_PRODUCTION and any(
    not origin.startswith("https://")
    for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured(
        "Les origines CSRF de production doivent utiliser https://."
    )


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'api',
    'accounts',
    'predictor',  # Notre application
]

MIDDLEWARE = [
    'student_satisfaction_project.i18n_middleware.UnifiedEnglishI18nMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "django.middleware.locale.LocaleMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    "accounts.middleware.RbacAccessMiddleware",
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# WhiteNoise n'est activé que dans l'environnement de production.
# Cela évite d'interférer avec le serveur statique Django en développement
# et avec le test runner.
if IS_PRODUCTION:
    _security_index = MIDDLEWARE.index(
        "django.middleware.security.SecurityMiddleware"
    )
    MIDDLEWARE.insert(
        _security_index + 1,
        "whitenoise.middleware.WhiteNoiseMiddleware",
    )



ROOT_URLCONF = 'student_satisfaction_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'template'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "accounts.context_processors.rbac_context",
            ],
        },
    },
]

WSGI_APPLICATION = 'student_satisfaction_project.wsgi.application'

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "",
).strip()

if DATABASE_URL:
    if IS_PRODUCTION and not DATABASE_URL.lower().startswith(
        ("postgres://", "postgresql://")
    ):
        raise ImproperlyConfigured(
            "DATABASE_URL doit utiliser PostgreSQL en production."
        )

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600 if IS_PRODUCTION else 0,
            conn_health_checks=IS_PRODUCTION,
        )
    }
elif IS_PRODUCTION:
    raise ImproperlyConfigured(
        "DATABASE_URL PostgreSQL est obligatoire en production."
    )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = Path(
    os.environ.get(
        "DJANGO_STATIC_ROOT",
        str(BASE_DIR / "staticfiles"),
    )
)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if IS_PRODUCTION
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

WHITENOISE_MAX_AGE = 31536000 if IS_PRODUCTION else 0


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login_register'

# Configuration pour les fichiers uploadés
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Journal applicatif minimal : les erreurs techniques restent côté serveur.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "predictor": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# V13 — API REST / JWT / OpenAPI
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "prediction": "120/min",
        "batch_prediction": "30/min",
        "api_readonly": "120/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "UPDATE_LAST_LOGIN": False,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API Satisfaction Étudiante",
    "DESCRIPTION": (
        "API REST du classifieur MLP de satisfaction étudiante. "
        "Les endpoints de prédiction utilisent le même moteur que l'interface Django."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": [
        "rest_framework.permissions.AllowAny",
    ],
}

# V14B — récupération de compte en développement
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "noreply@student-satisfaction.local",
)

SERVER_EMAIL = os.environ.get(
    "SERVER_EMAIL",
    DEFAULT_FROM_EMAIL,
)

EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = _env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = _env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = _env_int("EMAIL_TIMEOUT", 10)

if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured(
        "EMAIL_USE_TLS et EMAIL_USE_SSL ne peuvent pas être actifs ensemble."
    )


# V17.1 — HTTPS / cookies / reverse proxy
SECURE_SSL_REDIRECT = _env_bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    IS_PRODUCTION,
)

SESSION_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_HTTPONLY = True

SECURE_HSTS_SECONDS = _env_int(
    "DJANGO_HSTS_SECONDS",
    3600 if IS_PRODUCTION else 0,
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool(
    "DJANGO_HSTS_INCLUDE_SUBDOMAINS",
    False,
)
SECURE_HSTS_PRELOAD = _env_bool(
    "DJANGO_HSTS_PRELOAD",
    False,
)

SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if _env_bool(
        "DJANGO_TRUST_X_FORWARDED_PROTO",
        False,
    )
    else None
)

# V14C — internationalisation FR / EN
LANGUAGE_CODE = "fr"
LANGUAGES = (
    ("fr", "Français"),
    ("en", "English"),
)
LOCALE_PATHS = [
    BASE_DIR / "locale",
]
USE_I18N = True
