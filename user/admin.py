from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, OAuthProvider, UserOAuth
from django.contrib import messages

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'email', 'nickname', 'phone', 'is_verified', 'is_staff', 'date_joined', 'is_premium', 'premium_expiry')
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'date_joined', 'is_premium')
    search_fields = ('username', 'email', 'nickname', 'phone')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('个人信息'), {'fields': ('email', 'nickname', 'avatar', 'phone')}),
        (_('状态信息'), {'fields': ('is_verified', 'is_premium', 'premium_expiry')}),
        (_('权限'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('设置'), {'fields': ('language', 'timezone')}),
        (_('统计'), {'fields': ('login_count', 'last_login_ip')}),
        (_('重要日期'), {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('login_count', 'last_login_ip', 'last_login', 'date_joined')

@admin.register(OAuthProvider)
class OAuthProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'app_id', 'is_active', 'created_at')
    list_filter = ('is_active', 'name')
    search_fields = ('name', 'app_id')
    fieldsets = (
        (None, {'fields': ('name', 'app_id', 'is_active')}),
        (_('凭证'), {'fields': ('client_id', 'client_secret', 'redirect_uri')}),
        (_('苹果登录配置'), {'fields': ('team_id', 'key_id', 'private_key', 'private_key_path'), 
                      'classes': ('collapse',), 
                      'description': _('仅苹果登录需要填写这些字段')}),
        (_('高级设置'), {'fields': ('extra_config',)}),
    )
    
    def save_model(self, request, obj, form, change):
        # 处理上传的 p8 文件
        if obj.private_key_path and not obj.private_key:
            try:
                # 读取上传的文件内容
                obj.private_key = obj.private_key_path.read().decode('utf-8')
            except Exception as e:
                self.message_user(request, f"读取私钥文件失败: {str(e)}", level=messages.ERROR)
        
        super().save_model(request, obj, form, change)

@admin.register(UserOAuth)
class UserOAuthAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'provider_user_id', 'created_at')
    list_filter = ('provider', 'created_at')
    search_fields = ('user__username', 'user__email', 'provider_user_id')
    raw_id_fields = ('user', 'provider')
    readonly_fields = ('provider_user_id', 'access_token', 'refresh_token', 'expires_at', 'raw_data', 'created_at', 'updated_at')
