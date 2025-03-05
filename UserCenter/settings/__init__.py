"""
根据环境变量加载适当的设置
"""
import os

# 获取当前环境
ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')

# 根据环境导入适当的设置
if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'testing':
    from .testing import *
else:
    from .development import * 