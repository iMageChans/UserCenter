"""
WSGI config for UserCenter project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# 从环境变量获取设置模块，默认使用 'UserCenter.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UserCenter.settings')

application = get_wsgi_application()
