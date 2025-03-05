#!/usr/bin/env python
"""
本地开发辅助脚本
用法: python local_dev.py [django命令]
例如: python local_dev.py makemigrations
"""
import os
import sys
import django

# 设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UserCenter.settings')
os.environ.setdefault('DJANGO_ENV', 'development')

def main():
    """运行Django命令"""
    if len(sys.argv) < 2:
        print("请指定Django命令")
        print("用法: python local_dev.py [django命令]")
        print("例如: python local_dev.py makemigrations")
        return
    
    # 导入需要的模块
    from django.core.management import execute_from_command_line
    
    # 直接执行Django命令
    execute_from_command_line(['manage.py'] + sys.argv[1:])

if __name__ == '__main__':
    main() 