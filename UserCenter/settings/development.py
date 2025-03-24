"""
开发环境特定设置
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# 数据库设置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# # 如果提供了 PostgreSQL 配置，则使用 PostgreSQL
# if os.environ.get('DB_NAME'):
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.postgresql',
#             'NAME': os.environ.get('DB_NAME'),
#             'USER': os.environ.get('DB_USER'),
#             'PASSWORD': os.environ.get('DB_PASSWORD'),
#             'HOST': os.environ.get('DB_HOST', 'localhost'),
#             'PORT': os.environ.get('DB_PORT', '5432'),
#         }
#     }

# 缓存设置
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# 如果提供了 Redis URL，则使用 Redis 作为缓存
if os.environ.get('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }

# 邮件设置
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS 设置
CORS_ALLOW_ALL_ORIGINS = True

# 日志设置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
} 