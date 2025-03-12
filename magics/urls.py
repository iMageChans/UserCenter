from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'codes', views.MagicCodeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('redeem/', views.redeem_code, name='redeem-code'),
] 