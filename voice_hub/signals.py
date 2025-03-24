from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Feedback


@receiver(post_save, sender=Feedback)
def notify_admin_on_new_feedback(sender, instance, created, **kwargs):
    """当新反馈创建时通知管理员"""
    if created and hasattr(settings, 'ADMIN_EMAIL'):
        subject = f'新的反馈: {instance.get_feedback_type_display()}'
        message = f"""
        收到新的反馈:
        
        类型: {instance.get_feedback_type_display()}
        平台: {instance.get_platform_display()}
        应用ID: {instance.app_id}
        反馈者邮箱: {instance.email or '未提供'}
        内容: {instance.content}
        
        请登录管理后台查看详情。
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=True,
        ) 