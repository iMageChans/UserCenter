"""
基本设置文件，包含所有环境共享的设置
"""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

import environ
from django.utils.translation import gettext_lazy as _

# 初始化环境变量
env = environ.Env()

# 读取 .env 文件
environ.Env.read_env()

# 构建路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 安全设置
SECRET_KEY = env('SECRET_KEY', default='django-insecure-oi#*_o+3&81=&r&zy+#q3p3^7kc0=mfpd5kmf-p9213ax#%krr')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = ['localhost',
                 '127.0.0.1',
                 'pocket.pulseheath.com']

FORCE_SCRIPT_NAME = '/users'

# 应用定义
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 第三方应用
    'rest_framework',
    'rest_framework.authtoken',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # 社交账号提供商
    'allauth.socialaccount.providers.apple',
    'allauth.socialaccount.providers.weixin',
    'oauth2_provider',
    'corsheaders',
    
    # 自定义应用
    'user.apps.UserConfig',
    'magics.apps.MagicsConfig',
    'rosetta',  # 翻译管理界面
    'drf_yasg',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 应该放在最前面
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # 添加这一行，用于语言切换
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # 添加这一行
]

ROOT_URLCONF = 'UserCenter.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'UserCenter.wsgi.application'

# 数据库
DATABASES = {
    'default': env.db('DATABASE_URL', default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}")
}

# 密码验证
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

# 国际化
USE_I18N = True
USE_L10N = True
USE_TZ = True

# 支持的语言
LANGUAGES = [
    ('zh-hans', '简体中文'),
    ('en', 'English'),
    ('es', 'Español'),  # 西班牙语
    ('pt', 'Português'),  # 葡萄牙语
    ('fr', 'Français'),  # 法语
    ('ja', '日本語'),  # 日语
    ('ko', '한국어'),  # 韩语
]

# 默认语言
LANGUAGE_CODE = 'zh-hans'

# 翻译文件路径
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# 静态文件设置
STATIC_URL = '/static/users-service/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 媒体文件配置
MEDIA_URL = '/media/users-service/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# REST Framework 设置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'user.authentication.BearerTokenAuthentication',  # 使用自定义认证类
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# 默认主键字段类型
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 缓存设置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 邮件设置
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)

# 日志设置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# 自定义用户模型
AUTH_USER_MODEL = 'user.User'

# Django AllAuth设置
AUTHENTICATION_BACKENDS = [
    # Django管理后台登录
    'django.contrib.auth.backends.ModelBackend',
    # AllAuth邮箱登录
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_ADAPTER = 'user.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'user.adapters.CustomSocialAccountAdapter'

# OAuth2设置
OAUTH2_PROVIDER = {
    'SCOPES': {'read': 'Read scope', 'write': 'Write scope'},
    'ACCESS_TOKEN_EXPIRE_SECONDS': 86400,  # 24小时
}

# CORS设置
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_WHITELIST = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    # 添加您的前端域名
]

# Swagger设置
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Token': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': True,
    'VALIDATOR_URL': None,
    'DEFAULT_INFO': 'UserCenter.urls.api_info',
}

# 时区设置
TIME_ZONE = 'Asia/Shanghai' 