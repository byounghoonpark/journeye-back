from pathlib import Path
import os
from datetime import timedelta
import json
import sentry_sdk
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-1t#x^x30(pbukm9edejt@#ce&g#()d-#ag()p*^1=j+snrp)th'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

CORS_ALLOWED_HOSTS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

# CORS 설정 추가
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "ws://127.0.0.1:8001",
    "ws://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost:8001",
]

SECURE_PROXY_SSL_HEADER = None
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False


INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django_extensions',
    'corsheaders',
    'storages',
    'chat',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_yasg',
    'channels',
    'spaces',
    'accounts',
    'bookings',
    'concierge',
    'notifications'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'hotel_admin.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hotel_admin.wsgi.application'

ASGI_APPLICATION = 'hotel_admin.asgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

with open(os.path.join(BASE_DIR, 'secrets.json')) as config_file:
    secret_config = json.load(config_file)

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get("DB_NAME", "postgres"),
        'USER': os.environ.get("DB_USER", "postgres"),
        'PASSWORD': os.environ.get("DB_PASSWORD", "12345678"),
        'HOST': os.environ.get("DB_HOST", "db"),
        'PORT': os.environ.get("DB_PORT", "5432"),
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (
                    os.environ.get("REDIS_HOST", "redis"),
                    int(os.environ.get("REDIS_PORT", "6379"))
                )
            ],
        },
    },
}
# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

# TIME_ZONE = 'UTC'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),  # 액세스 토큰 유효 시간
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),  # 리프레시 토큰 유효 시간
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": "your_secret_key_here",  # 실제 운영에서는 .env 파일에서 로드해야 함
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT 인증을 위한 Bearer 토큰을 입력하세요. 예: Bearer <your_token>"
        }
    },
    "USE_SESSION_AUTH": False,  # Django 로그인 제거
    "JSON_EDITOR": True,
}

# 이메일 설정
EMAIL_BACKEND = secret_config['EMAIL_BACKEND']
EMAIL_HOST = secret_config['EMAIL_HOST']
EMAIL_PORT = secret_config['EMAIL_PORT']
EMAIL_USE_TLS = secret_config['EMAIL_USE_TLS']
EMAIL_HOST_USER = secret_config['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = secret_config['EMAIL_HOST_PASSWORD']
DEFAULT_FROM_EMAIL = secret_config['DEFAULT_FROM_EMAIL']


sentry_sdk.init(
    dsn="https://d03ae81cfd030d715717aa27a9ec8bac@sentry.alluser.net/3",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

MEDIA_URL = '/photos/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'photos')

DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

AWS_ACCESS_KEY_ID = "admin"  # MinIO ID
AWS_SECRET_ACCESS_KEY = "admin123"  # MinIO Password
AWS_STORAGE_BUCKET_NAME = "mybucket"  # 생성한 버킷 이름
AWS_S3_ENDPOINT_URL = "http://localhost:9000"  # MinIO API 주소
AWS_S3_ADDRESSING_STYLE = "path"  # Path-style URL 사용
AWS_S3_CUSTOM_DOMAIN = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}"


DEEPL_API_KEY = secret_config['DEEPL_API_KEY']