from django.contrib import admin
from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'feedback_type', 'platform', 'app_id', 'email', 'is_processed', 'created_at')
    list_filter = ('feedback_type', 'platform', 'is_processed', 'created_at')
    search_fields = ('email', 'content', 'app_id')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_processed',)
    date_hierarchy = 'created_at'
    fieldsets = (
        ('基本信息', {
            'fields': ('feedback_type', 'platform', 'app_id', 'email')
        }),
        ('反馈内容', {
            'fields': ('content',)
        }),
        ('处理状态', {
            'fields': ('is_processed',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
