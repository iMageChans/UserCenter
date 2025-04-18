from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    自定义用户模型，扩展Django默认用户
    """
    # 用户基本信息
    nickname = models.CharField(_('昵称'), max_length=50, blank=True)
    avatar = models.URLField(_('头像URL'), blank=True)
    phone = models.CharField(_('手机号'), max_length=20, blank=True, unique=True, null=True)
    
    # 第三方账号关联信息
    is_verified = models.BooleanField(_('是否验证'), default=False)
    
    # 用户设置
    language = models.CharField(_('语言偏好'), max_length=10, default='zh-hans')
    timezone = models.CharField(_('时区'), max_length=50, default='Asia/Shanghai')
    
    # 付费用户信息
    is_premium = models.BooleanField(_('是否付费用户'), default=False)
    premium_expiry = models.DateTimeField(_('付费到期时间'), null=True, blank=True)
    
    # 用户统计
    login_count = models.IntegerField(_('登录次数'), default=0)
    last_login_ip = models.GenericIPAddressField(_('最后登录IP'), blank=True, null=True)
    
    # 元数据
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)


    # 匿名用户标识
    is_anonymous_user = models.BooleanField(default=False, verbose_name=_('是否为匿名用户'))
    
    class Meta:
        verbose_name = _('用户')
        verbose_name_plural = _('用户')
        
    def __str__(self):
        return self.nickname or self.username

class OAuthProvider(models.Model):
    """
    OAuth提供商配置
    """
    PROVIDER_CHOICES = (
        # 中国大陆
        ('wechat', _('微信')),
        ('qq', _('QQ')),
        ('weibo', _('微博')),
        ('alipay', _('支付宝')),
        ('dingtalk', _('钉钉')),
        
        # 国际
        ('apple', _('苹果')),
        ('google', _('谷歌')),
        ('facebook', _('脸书')),
        ('twitter', _('推特')),
        ('github', _('GitHub')),
        ('linkedin', _('领英')),
    )
    
    name = models.CharField(_('名称'), max_length=20, choices=PROVIDER_CHOICES)
    app_id = models.CharField(_('应用ID'), max_length=100, default='default', help_text=_('用于区分不同的应用'))
    client_id = models.CharField(_('客户端ID'), max_length=255)
    client_secret = models.CharField(_('客户端密钥'), max_length=255)
    redirect_uri = models.URLField(_('回调URL'))
    is_active = models.BooleanField(_('是否启用'), default=True)
    
    # 额外配置，存储为JSON
    extra_config = models.JSONField(_('额外配置'), default=dict, blank=True)
    
    # 苹果登录专用字段
    team_id = models.CharField(_('团队ID'), max_length=100, blank=True, help_text=_('苹果开发者团队ID'))
    key_id = models.CharField(_('密钥ID'), max_length=100, blank=True, help_text=_('苹果密钥ID'))
    private_key = models.TextField(_('私钥'), blank=True, help_text=_('苹果登录私钥内容'))
    private_key_path = models.FileField(_('私钥文件'), upload_to='apple_keys/', blank=True, null=True, help_text=_('苹果登录私钥文件'))
    
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('OAuth提供商')
        verbose_name_plural = _('OAuth提供商')
        unique_together = ('name', 'app_id')  # 确保每个应用的每种提供商只有一个配置
        
    def __str__(self):
        return f"{self.get_name_display()} - {self.app_id}"

class UserOAuth(models.Model):
    """
    用户OAuth账号关联
    """
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='oauth_accounts')
    provider = models.ForeignKey(OAuthProvider, on_delete=models.CASCADE)
    
    # OAuth账号信息
    provider_user_id = models.CharField(_('第三方用户ID'), max_length=255)
    access_token = models.TextField(_('访问令牌'))
    refresh_token = models.TextField(_('刷新令牌'), blank=True)
    expires_at = models.DateTimeField(_('过期时间'), null=True, blank=True)
    
    # 用户在第三方平台的信息
    raw_data = models.JSONField(_('原始数据'), default=dict)
    
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('用户OAuth账号')
        verbose_name_plural = _('用户OAuth账号')
        unique_together = ('provider', 'provider_user_id')
        
    def __str__(self):
        return f"{self.user} - {self.provider}"
