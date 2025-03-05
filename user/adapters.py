from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest

class CustomAccountAdapter(DefaultAccountAdapter):
    """
    自定义账号适配器
    """
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        # 设置默认值
        user.language = getattr(settings, 'LANGUAGE_CODE', 'zh-hans')
        user.timezone = getattr(settings, 'TIME_ZONE', 'Asia/Shanghai')
        
        if commit:
            user.save()
        return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    自定义社交账号适配器
    """
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        
        # 从社交账号获取额外信息
        if sociallogin.account.provider == 'weixin':
            user.nickname = data.get('nickname', '')
            user.avatar = data.get('headimgurl', '')
        elif sociallogin.account.provider == 'apple':
            # Apple登录可能没有提供名称
            pass
        elif sociallogin.account.provider == 'google':
            user.nickname = data.get('name', '')
            user.avatar = data.get('picture', '')
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        
        # 标记为已验证
        user.is_verified = True
        user.save()
        
        # 记录登录IP
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                user.last_login_ip = x_forwarded_for.split(',')[0]
            else:
                user.last_login_ip = request.META.get('REMOTE_ADDR')
            user.login_count += 1
            user.save(update_fields=['last_login_ip', 'login_count'])
        
        return user 