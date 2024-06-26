"""Django settings for core project."""

import os
import datetime
from pathlib import Path
from concurrent_log_handler.queue import setup_logging_queues

#################################################
# Directories                                   #
#################################################
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_LOGS = os.environ.get("BASE_LOGS", "/logs/")
BASE_DATA = os.environ.get("BASE_DATA", "/")
CONSUME_DIR = os.environ.get("CONSUME_DIR", os.path.join(BASE_DATA, "consume"))
MEDIA_ROOT = os.path.join(BASE_DATA, "protected_media")
STATIC_ROOT = os.path.join(BASE_DIR, "static")
PHOTOS = os.environ.get("PHOTOS", os.path.join(BASE_DATA, "data"))
UPLOAD_ROOT = os.environ.get("UPLOADS", os.path.join(MEDIA_ROOT, "uploads"))
IM2TXT_ROOT = os.path.join(MEDIA_ROOT, "data_models", "im2txt")
IM2TXT_ONNX_ROOT = os.path.join(MEDIA_ROOT, "data_models", "im2txt_onnx")
BLIP_ROOT = os.path.join(MEDIA_ROOT, "data_models", "blip")
PLACES365_ROOT = os.path.join(MEDIA_ROOT, "data_models", "places365", "model")
LOGS_ROOT = BASE_LOGS

#################################################
# URLs                                          #
#################################################

MEDIA_URL = "/media/"

STATIC_URL = "api/static/"

ROOT_URLCONF = "core.urls"

#################################################
# Security                                      #
#################################################

SECRET_KEY_FILENAME = os.path.join(BASE_LOGS, "secret.key")
SECRET_KEY = ""

if os.environ.get("SECRET_KEY"):
    SECRET_KEY = os.environ["SECRET_KEY"]
    print("using SECRET_KEY from env")

if not SECRET_KEY and os.path.exists(SECRET_KEY_FILENAME):
    with open(SECRET_KEY_FILENAME, "r") as f:
        SECRET_KEY = f.read().strip()
        print("using SECRET_KEY from file")

if not SECRET_KEY:
    from django.core.management.utils import get_random_secret_key

    with open(SECRET_KEY_FILENAME, "w") as f:
        f.write(get_random_secret_key())
        print("generating SECRET_KEY and saving to file")
    with open(SECRET_KEY_FILENAME, "r") as f:
        SECRET_KEY = f.read().strip()
        print("using SECRET_KEY from file")

DEBUG = os.environ.get("DEBUG", "True")

ALLOWED_HOSTS = ["localhost", os.environ.get("BACKEND_HOST", "backend")]

AUTH_USER_MODEL = "api.User"

#################################################
# Localization                                  #
#################################################

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

#################################################
# Installed Apps                                #
#################################################

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "api",
    "chunked_upload",
    "corsheaders",
    "django_extensions",
    "django_filters",
    "django_q",
    "rest_framework",
    "taggit",
]

if DEBUG:
    INSTALLED_APPS.append("drf_yasg")

#################################################
# Middleware                                    #
#################################################

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

#################################################
# Templates                                     #
#################################################

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

#################################################
# Database                                      #
#################################################

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "soocphotos"),
        "USER": os.environ.get("DB_USER", "soocphotos_user"),
        "PASSWORD": os.environ.get("DB_PASS", "AaAa1234"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

#################################################
# Password Validation                           #
#################################################

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

#################################################
# Miscellaneous                                 #
#################################################

WSGI_APPLICATION = "core.wsgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DEFAULT_FAVORITE_MIN_RATING = os.environ.get("DEFAULT_FAVORITE_MIN_RATING", 4)

LLM_MODEL = os.environ.get("LLM_MODEL", "mistral-7b-v0.1.Q5_K_M")

CAPTIONING_MODEL = os.environ.get("CAPTIONING_MODEL", "im2txt")

MAP_API_PROVIDER = os.environ.get("MAP_API_PROVIDER", "photon")

MAP_API_KEY = os.environ.get("MAP_API_KEY", "")

SKIP_PATTERNS = os.environ.get("SKIP_PATTERNS", ".")

ALLOW_UPLOAD = os.environ.get("ALLOW_UPLOAD", "True")

#################################################
# Rest Framework                                #
#################################################

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20000,
}

REST_FRAMEWORK_EXTENSIONS = {
    "DEFAULT_OBJECT_CACHE_KEY_FUNC": "rest_framework_extensions.utils.default_object_cache_key_func",  # pylint: disable=line-too-long
    "DEFAULT_LIST_CACHE_KEY_FUNC": "rest_framework_extensions.utils.default_list_cache_key_func",
}

#################################################
# Simple JWT                                    #
#################################################

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=7),
}

#################################################
# Logging                                       #
#################################################

setup_logging_queues()

if not os.path.exists(BASE_LOGS):
    os.mkdir(BASE_LOGS)

LOGROTATE_MAX_SIZE = 1024 * 1024  # 1MB
LOGROTATE_MAX_BACKUPS = 20
ASYNC_LOGGING = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s : %(filename)s : %(funcName)s : %(lineno)s : %(levelname)s : %(message)s",  # pylint: disable=line-too-long
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file_exif": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_LOGS, "exif.log"),
            "maxBytes": LOGROTATE_MAX_SIZE,
            "backupCount": LOGROTATE_MAX_BACKUPS,
        },
        "file_face_recognition": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_LOGS, "face_recognition.log"),
            "maxBytes": LOGROTATE_MAX_SIZE,
            "backupCount": LOGROTATE_MAX_BACKUPS,
        },
        "file_llm": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_LOGS, "llm.log"),
            "maxBytes": LOGROTATE_MAX_SIZE,
            "backupCount": LOGROTATE_MAX_BACKUPS,
        },
        "file_places365": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_LOGS, "places365.log"),
            "maxBytes": LOGROTATE_MAX_SIZE,
            "backupCount": LOGROTATE_MAX_BACKUPS,
        },
        "file_soocphotos": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_LOGS, "soocphotos.log"),
            "maxBytes": LOGROTATE_MAX_SIZE,
            "backupCount": LOGROTATE_MAX_BACKUPS,
        },
        "file_thumbnails": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_LOGS, "thumbnails.log"),
            "maxBytes": LOGROTATE_MAX_SIZE,
            "backupCount": LOGROTATE_MAX_BACKUPS,
        },
        "file_image_captioning": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_LOGS, "image_captioning.log"),
            "maxBytes": LOGROTATE_MAX_SIZE,
            "backupCount": LOGROTATE_MAX_BACKUPS,
        },
        "file_image_similarity": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_LOGS, "image_similarity.log"),
            "maxBytes": LOGROTATE_MAX_SIZE,
            "backupCount": LOGROTATE_MAX_BACKUPS,
        },
        "file_django_q": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "formatter": "verbose",
            "filename": os.path.join(BASE_LOGS, "django_q.log"),
            "maxBytes": LOGROTATE_MAX_SIZE,
            "backupCount": LOGROTATE_MAX_BACKUPS,
        },
    },
    "root": {"handlers": ["console"]},
    "loggers": {
        "exif": {"handlers": ["file_exif"], "level": "DEBUG"},
        "face_recognition": {"handlers": ["file_face_recognition"], "level": "DEBUG"},
        "llm": {"handlers": ["file_llm"], "level": "DEBUG"},
        "places365": {"handlers": ["file_places365"], "level": "DEBUG"},
        "soocphotos": {"handlers": ["file_soocphotos"], "level": "DEBUG"},
        "thumbnails": {"handlers": ["file_thumbnails"], "level": "DEBUG"},
        "image_captioning": {"handlers": ["file_image_captioning"], "level": "DEBUG"},
        "image_similarity": {"handlers": ["file_image_similarity"], "level": "DEBUG"},
        "django_q": {"handlers": ["file_django_q"], "level": "DEBUG"},
    },
}

#################################################
# Heavyweight Process                           #
# - Must be less or equal of # of CPU cores     #
# - (Nearly 2GB per process)                    #
#################################################

HEAVYWEIGHT_PROCESS_ENV = os.environ.get("HEAVYWEIGHT_PROCESS", "1")
HEAVYWEIGHT_PROCESS = (
    int(HEAVYWEIGHT_PROCESS_ENV) if HEAVYWEIGHT_PROCESS_ENV.isnumeric() else 1
)

#################################################
# Q_Cluster                                     #
#################################################

Q_CLUSTER = {
    "name": "DjangORM",
    "workers": HEAVYWEIGHT_PROCESS,
    "queue_limit": 50,
    "timeout": 10000000,
    "retry": 20000000,
    "orm": "default",
}

#################################################
# CORS                                          #
#################################################

CORS_ALLOW_HEADERS = (
    "cache-control",
    "accept",
    "accept-encoding",
    "allow-credentials",
    "withcredentials",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
)

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = ["http://127.0.0.1:3000"]

if os.environ.get("CORS_ALLOWED_ORIGINS"):
    CORS_ALLOWED_ORIGINS.append(os.environ.get("CORS_ALLOWED_ORIGINS"))

#################################################
# CSRF                                          #
#################################################

CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:3000"]
if os.environ.get("CSRF_TRUSTED_ORIGINS"):
    CSRF_TRUSTED_ORIGINS.append(os.environ.get("CSRF_TRUSTED_ORIGINS"))

#################################################
# Taggit                                        #
#################################################

TAGGIT_CASE_INSENSITIVE = True
