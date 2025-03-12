from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import random
import string
from user.models import User

class MagicCode(models.Model):
    """优惠码模型"""
    
    STATUS_CHOICES = (
        ('active', _('有效')),
        ('expired', _('已过期')),
        ('used_up', _('已用完')),
        ('disabled', _('已禁用')),
    )
    
    code = models.CharField(_('优惠码'), max_length=20, unique=True)
    app_id = models.CharField(_('应用ID'), max_length=100, default='default', help_text=_('用于区分不同的应用'))
    days = models.IntegerField(_('会员天数'), default=30, help_text=_('兑换后获得的会员天数'))
    max_uses = models.IntegerField(_('最大使用次数'), default=1, help_text=_('优惠码可以使用的最大次数'))
    used_count = models.IntegerField(_('已使用次数'), default=0, help_text=_('优惠码已被使用的次数'))
    status = models.CharField(_('状态'), max_length=10, choices=STATUS_CHOICES, default='active')
    
    expires_at = models.DateTimeField(_('过期时间'), null=True, blank=True, help_text=_('优惠码的过期时间'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_codes', verbose_name=_('创建者'))
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    
    class Meta:
        verbose_name = _('优惠码')
        verbose_name_plural = _('优惠码')
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"
    
    @classmethod
    def generate_code(cls, length=8, prefix=''):
        """生成随机优惠码"""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = prefix + ''.join(random.choice(chars) for _ in range(length))
            if not cls.objects.filter(code=code).exists():
                return code
    
    def is_valid(self):
        """检查优惠码是否有效"""
        if self.status != 'active':
            return False
        
        if self.expires_at and self.expires_at < timezone.now():
            self.status = 'expired'
            self.save(update_fields=['status'])
            return False
        
        if self.used_count >= self.max_uses:
            self.status = 'used_up'
            self.save(update_fields=['status'])
            return False
        
        return True
    
    def use(self, user):
        """使用优惠码"""
        if not self.is_valid():
            return False
        
        # 检查用户是否已经使用过此优惠码
        if MagicCodeUsage.objects.filter(code=self, user=user).exists():
            return False
        
        # 记录使用情况
        usage = MagicCodeUsage.objects.create(
            code=self,
            user=user
        )
        
        # 更新使用次数
        self.used_count += 1
        if self.used_count >= self.max_uses:
            self.status = 'used_up'
        self.save(update_fields=['used_count', 'status'])
        
        # 更新用户会员状态
        if user.is_premium and user.premium_expiry and user.premium_expiry > timezone.now():
            # 如果用户已经是会员且未过期，则累加时间
            user.premium_expiry = user.premium_expiry + timezone.timedelta(days=self.days)
        else:
            # 否则从当前时间开始计算
            user.is_premium = True
            user.premium_expiry = timezone.now() + timezone.timedelta(days=self.days)
        
        user.save(update_fields=['is_premium', 'premium_expiry'])
        return True

class MagicCodeUsage(models.Model):
    """优惠码使用记录"""
    code = models.ForeignKey(MagicCode, on_delete=models.CASCADE, related_name='usages', verbose_name=_('优惠码'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='code_usages', verbose_name=_('用户'))
    used_at = models.DateTimeField(_('使用时间'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('优惠码使用记录')
        verbose_name_plural = _('优惠码使用记录')
        unique_together = ('code', 'user')  # 每个用户只能使用一个特定的优惠码一次
        
    def __str__(self):
        return f"{self.user.username} 使用了 {self.code.code}"
