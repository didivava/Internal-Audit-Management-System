import json
import os
from pathlib import Path
from uuid import UUID
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("DJANGO_DEBUG")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "local-development-only-not-for-production"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be configured outside development.")
if not DEBUG and SECRET_KEY == "local-development-only-not-for-production":
    raise ImproperlyConfigured("Set a unique DJANGO_SECRET_KEY before deployment.")
if not DEBUG and (len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must contain at least 50 characters with sufficient entropy.")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be configured outside development.")

ENTRA_TENANT_ID = os.environ.get("ENTRA_TENANT_ID", "").strip()
ENTRA_CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID", "").strip()
ENTRA_CLIENT_SECRET = os.environ.get("ENTRA_CLIENT_SECRET", "")
oidc_values = (ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET)
OIDC_ENABLED = any(oidc_values)
if OIDC_ENABLED and not all(oidc_values):
    raise ImproperlyConfigured(
        "Configure ENTRA_TENANT_ID, ENTRA_CLIENT_ID, and ENTRA_CLIENT_SECRET together."
    )
if not DEBUG and not OIDC_ENABLED:
    raise ImproperlyConfigured("Microsoft Entra OIDC must be configured outside development.")

if OIDC_ENABLED:
    try:
        ENTRA_TENANT_ID = str(UUID(ENTRA_TENANT_ID))
    except ValueError as exc:
        raise ImproperlyConfigured("ENTRA_TENANT_ID must be a Microsoft Entra tenant GUID.") from exc

    OIDC_EXPECTED_ISSUER = (
        f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/v2.0"
    )
    OIDC_RP_CLIENT_ID = ENTRA_CLIENT_ID
    OIDC_RP_CLIENT_SECRET = ENTRA_CLIENT_SECRET
    OIDC_RP_SIGN_ALGO = "RS256"
    OIDC_RP_SCOPES = "openid profile email"
    OIDC_OP_AUTHORIZATION_ENDPOINT = (
        f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/oauth2/v2.0/authorize"
    )
    OIDC_OP_TOKEN_ENDPOINT = (
        f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/oauth2/v2.0/token"
    )
    OIDC_OP_USER_ENDPOINT = "https://graph.microsoft.com/oidc/userinfo"
    OIDC_OP_JWKS_ENDPOINT = (
        f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}/discovery/v2.0/keys"
    )
    OIDC_USE_NONCE = True
    OIDC_USE_PKCE = True
    OIDC_VERIFY_SSL = True
    OIDC_VERIFY_KID = True
    OIDC_ALLOW_UNSECURED_JWT = False
    OIDC_TIMEOUT = 10
    OIDC_STORE_ACCESS_TOKEN = False
    OIDC_STORE_ID_TOKEN = False
    OIDC_CREATE_USER = True
    ENTRA_ROLE_CLAIM = os.environ.get("ENTRA_ROLE_CLAIM", "roles").strip()
    try:
        ENTRA_ROLE_GROUP_MAPPING = json.loads(
            os.environ.get("ENTRA_ROLE_GROUP_MAPPING", "{}")
        )
    except json.JSONDecodeError as exc:
        raise ImproperlyConfigured("ENTRA_ROLE_GROUP_MAPPING must contain a JSON object.") from exc
    if not ENTRA_ROLE_CLAIM or not isinstance(ENTRA_ROLE_GROUP_MAPPING, dict) or any(
        not isinstance(role, str)
        or not role
        or not isinstance(group, str)
        or not group
        or len(group) > 150
        for role, group in ENTRA_ROLE_GROUP_MAPPING.items()
    ):
        raise ImproperlyConfigured(
            "ENTRA_ROLE_CLAIM and role/group mappings must contain valid non-empty strings."
        )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts.apps.AccountsConfig",
    "core.apps.CoreConfig",
    "rest_framework",
    *([] if not OIDC_ENABLED else ["mozilla_django_oidc"]),
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    *([] if DEBUG else ["whitenoise.middleware.WhiteNoiseMiddleware"]),
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "audit_platform.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "audit_platform.wsgi.application"
ASGI_APPLICATION = "audit_platform.asgi.application"

database_url = os.environ.get("DATABASE_URL")
if database_url:
    parsed_database_url = urlparse(database_url)
    if parsed_database_url.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL must use the PostgreSQL scheme.")
    if not parsed_database_url.hostname or not parsed_database_url.path.strip("/"):
        raise ImproperlyConfigured("DATABASE_URL must include a PostgreSQL host and database name.")
    query = parse_qs(parsed_database_url.query)
    database_options = {}
    if query.get("sslmode"):
        database_options["sslmode"] = query["sslmode"][-1]
    elif not DEBUG:
        database_options["sslmode"] = os.environ.get("DATABASE_SSLMODE", "require")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed_database_url.path.lstrip("/")),
            "USER": unquote(parsed_database_url.username or ""),
            "PASSWORD": unquote(parsed_database_url.password or ""),
            "HOST": parsed_database_url.hostname,
            "PORT": parsed_database_url.port or "",
            "CONN_MAX_AGE": int(os.environ.get("DATABASE_CONN_MAX_AGE", "60")),
            "OPTIONS": database_options,
        }
    }
elif DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    raise ImproperlyConfigured("DATABASE_URL must point to PostgreSQL outside development.")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
if OIDC_ENABLED:
    AUTHENTICATION_BACKENDS.insert(0, "accounts.oidc.EntraOIDCBackend")
    LOGIN_URL = "/oidc/authenticate/"
    LOGIN_REDIRECT_URL = "/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = int(os.environ.get("DJANGO_SESSION_AGE_SECONDS", "28800"))
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS")
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD")
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    if env_bool("DJANGO_TRUST_PROXY_SSL"):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
