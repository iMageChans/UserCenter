from django.db import models
from django.utils.translation import gettext_lazy as _


class FeedbackType(models.TextChoices):
    BUG = 'BUG', _('Bug报告')
    FEED_BACK = 'Feedback', _('功能建议')
    QUESTION = 'Question', _('内容问题')
    PAYMENT = 'Payment', _('支付问题')
    OTHER = 'OTHER', _('其他')


class Platform(models.TextChoices):
    IOS = 'IOS', _('iOS')
    ANDROID = 'ANDROID', _('Android')
    WEB = 'WEB', _('Web')
    OTHER = 'OTHER', _('其他')


class Feedback(models.Model):
    """用户反馈模型"""
    email = models.EmailField(verbose_name=_('反馈者邮箱'), blank=True, null=True)
    feedback_type = models.CharField(
        max_length=20,
        choices=FeedbackType.choices,
        default=FeedbackType.OTHER,
        verbose_name=_('反馈类型')
    )
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
        default=Platform.IOS,
        verbose_name=_('平台')
    )
    app_id = models.CharField(max_length=100, verbose_name=_('应用ID'))
    content = models.TextField(verbose_name=_('反馈内容'))
    is_processed = models.BooleanField(default=False, verbose_name=_('是否已处理'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('更新时间'))

    class Meta:
        verbose_name = _('用户反馈')
        verbose_name_plural = _('用户反馈')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_feedback_type_display()} - {self.get_platform_display()} - {self.created_at.strftime('%Y-%m-%d')}"
