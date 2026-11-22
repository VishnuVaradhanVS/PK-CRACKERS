import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-local-development-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [x.strip() for x in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x.strip()]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "store",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "store.context_processors.login_legal_notice",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
# Render provides DATABASE_URL for its managed PostgreSQL service.
# Docker Compose also injects DATABASE_URL for the local PostgreSQL container.
# If neither is set, retain the existing SQLite fallback for local development.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DATABASES = {"default": dj_database_url.config(
    default=DATABASE_URL or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    conn_max_age=600, conn_health_checks=True,
)}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() == "true"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# Email notifications. Resend uses HTTPS, which is compatible with Render Free.
# Legacy SMTP remains available for local/paid deployments when explicitly selected.
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "").strip().lower()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"
if EMAIL_PROVIDER == "resend":
    EMAIL_BACKEND = "store.email_backends.ResendEmailBackend"
elif EMAIL_PROVIDER == "smtp" or EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
if os.getenv("DEFAULT_FROM_EMAIL"):
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
elif EMAIL_PROVIDER == "resend":
    DEFAULT_FROM_EMAIL = "PK CRACKERS <onboarding@resend.dev>"
else:
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or "webmaster@localhost"
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# Optional Meta WhatsApp Cloud API notifications. Keep credentials in environment variables.
WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "False").lower() == "true"
WHATSAPP_NOTIFY_CUSTOMERS = os.getenv("WHATSAPP_NOTIFY_CUSTOMERS", "True").lower() == "true"
WHATSAPP_NOTIFY_ADMINS = os.getenv("WHATSAPP_NOTIFY_ADMINS", "True").lower() == "true"
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v26.0")
WHATSAPP_TEMPLATE_LANGUAGE = os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "en")
WHATSAPP_DEFAULT_COUNTRY_CODE = os.getenv("WHATSAPP_DEFAULT_COUNTRY_CODE", "91").lstrip("+")
WHATSAPP_TEMPLATE_ORDER_CONFIRMATION = os.getenv("WHATSAPP_TEMPLATE_ORDER_CONFIRMATION", "kk_order_confirmation")
WHATSAPP_TEMPLATE_ORDER_UPDATE = os.getenv("WHATSAPP_TEMPLATE_ORDER_UPDATE", "kk_order_update")
WHATSAPP_TEMPLATE_ADMIN_NEW_ORDER = os.getenv("WHATSAPP_TEMPLATE_ADMIN_NEW_ORDER", "kk_admin_new_order")
