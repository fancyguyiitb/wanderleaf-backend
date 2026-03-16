import os
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
from corsheaders.defaults import default_headers
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


def _get_app_env() -> str:
    env = os.getenv("DJANGO_ENV", "development").strip().lower()
    return "production" if env in {"production", "prod"} else "development"


def _split_env_values(name: str) -> list[str]:
    raw = os.getenv(name, "").replace(",", " ")
    return [value.strip() for value in raw.split() if value.strip()]


def _get_env_url(dev_var: str, prod_var: str, app_env: str) -> str:
    selected_var = prod_var if app_env == "production" else dev_var
    value = os.getenv(selected_var, "").strip().rstrip("/")
    if not value:
        raise RuntimeError(f"{selected_var} must be set for {app_env} environment.")
    return value


APP_ENV = _get_app_env()
FRONTEND_BASE_URL = _get_env_url("FRONTEND_URL_DEV", "FRONTEND_URL_PROD", APP_ENV)
BACKEND_BASE_URL = _get_env_url("BACKEND_URL_DEV", "BACKEND_URL_PROD", APP_ENV)

_backend_hostname = urlparse(BACKEND_BASE_URL).hostname
_default_allowed_hosts = [_backend_hostname] if _backend_hostname else []
if APP_ENV == "development":
    _default_allowed_hosts.extend(["localhost", "127.0.0.1"])

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-secret-key")

DEBUG = False

ALLOWED_HOSTS: list[str] = _split_env_values("DJANGO_ALLOWED_HOSTS") or _default_allowed_hosts

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "dj_rest_auth",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "dj_rest_auth.registration",
    "channels",
    # Cloud media storage (ALL environments)
    "cloudinary_storage",
    "cloudinary",
    # project apps
    "apps.common.apps.CommonConfig",
    "apps.users.apps.UsersConfig",
    "apps.listings.apps.ListingsConfig",
    "apps.bookings.apps.BookingsConfig",
    "apps.payments.apps.PaymentsConfig",
    "apps.reviews.apps.ReviewsConfig",
    "apps.messaging.apps.MessagingConfig",
    "apps.wishlist.apps.WishlistConfig",
]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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


DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True),
    }
else:
    # Local development fallback (SQLite). This is weaker than Postgres for
    # bookings because select_for_update row locks and exclusion constraints
    # are not available here.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


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


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS: list[Path] = []

# Media files base URL (not used for local files; Cloudinary will generate full URLs)
MEDIA_URL = "/media/"

# Cloudinary configuration (used in ALL environments via STORAGES)
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

if not (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET):
    raise RuntimeError(
        "Cloudinary credentials are required. "
        "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET in your environment."
    )

import cloudinary  # noqa: E402
import cloudinary.api  # noqa: E402
import cloudinary.uploader  # noqa: E402

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
    "API_KEY": CLOUDINARY_API_KEY,
    "API_SECRET": CLOUDINARY_API_SECRET,
    # Force secure URLs (HTTPS)
    "SECURE": True,
}

# Django 5+ storage configuration
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,  # Force HTTPS URLs
)

# Razorpay (optional; used for booking payments)
RZP_TEST_KEY_ID = os.getenv("RZP_TEST_KEY_ID")
RZP_TEST_KEY_SECRET = os.getenv("RZP_TEST_KEY_SECRET")

# Email (optional; notifications are skipped when SMTP is selected without a host)
EMAIL_NOTIFICATIONS_ENABLED = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "true").lower() in ("true", "1", "yes")
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@wanderleaf.com")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"


CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "false").lower() == "true"
CORS_ALLOWED_ORIGINS = _split_env_values("CORS_ALLOWED_ORIGINS") or [FRONTEND_BASE_URL]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = _split_env_values("CSRF_TRUSTED_ORIGINS") or [
    FRONTEND_BASE_URL,
    BACKEND_BASE_URL,
]

CORS_ALLOW_HEADERS = list(default_headers) + [
    "idempotency-key",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

CHANNELS_REDIS_URL = os.getenv("CHANNELS_REDIS_URL") or os.getenv("CELERY_BROKER_URL")

if CHANNELS_REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [CHANNELS_REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
