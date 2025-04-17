from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'oauth-providers', views.OAuthProviderViewSet)
router.register(r'anonymous', views.AnonymousUserViewSet, basename='anonymous')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/', views.obtain_auth_token, name='api-token-auth'),
    path('auth/register/', views.register, name='api-register'),
    path('auth/social-login/', views.social_login, name='api-social-login'),
    path('languages/', views.get_available_languages, name='available_languages'),
    path('set-language/', views.set_language, name='set_language'),
] 