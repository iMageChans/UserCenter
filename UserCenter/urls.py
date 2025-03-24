"""
URL configuration for UserCenter project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.utils.translation import gettext_lazy as _

# API文档信息
api_info = openapi.Info(
    title="UserCenter API",
    default_version='v1',
    description="UserCenter OAuth用户系统API文档",
    terms_of_service="https://www.example.com/terms/",
    contact=openapi.Contact(email="contact@example.com"),
    license=openapi.License(name="BSD License"),
)

# 创建Schema视图
schema_view = get_schema_view(
    api_info,
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# 非国际化 URL
urlpatterns = [
    # 一些不需要国际化的 URL，如静态文件等
    path('i18n/', include('django.conf.urls.i18n')),  # 用于语言切换
]

# 国际化 URL 
urlpatterns += i18n_patterns(
    path(_('admin/'), admin.site.urls),
    path('api/', include('user.urls')),
    path('accounts/', include('allauth.urls')),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('rosetta/', include('rosetta.urls')),
    path('api/magics/', include('magics.urls')),
    path('api/voice/', include('voice_hub.urls')),
    
    # API文档URL
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    prefix_default_language=False  # 是否在默认语言的 URL 中添加语言前缀
)

# 添加 Debug Toolbar URL 配置
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
