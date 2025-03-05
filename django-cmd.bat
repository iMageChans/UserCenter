@echo off
set DJANGO_SETTINGS_MODULE=UserCenter.settings
set DJANGO_ENV=development
python manage.py %* 