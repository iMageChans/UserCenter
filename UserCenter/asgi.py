"""
ASGI config for UserCenter project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# 从环境变量获取设置模块，默认使用 'UserCenter.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UserCenter.settings')

application = get_asgi_application()
