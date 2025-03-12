from django.contrib import admin
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django import forms
from .models import MagicCode, MagicCodeUsage

class BatchCreateForm(forms.Form):
    """批量创建优惠码的表单"""
    count = forms.IntegerField(label=_('生成数量'), min_value=1, max_value=1000, initial=10)
    prefix = forms.CharField(label=_('优惠码前缀'), max_length=10, required=False, help_text=_('可选，优惠码的前缀'))
    app_id = forms.CharField(label=_('应用ID'), max_length=100, initial='default', help_text=_('用于区分不同的应用'))
    days = forms.IntegerField(label=_('会员天数'), min_value=1, initial=30)
    max_uses = forms.IntegerField(label=_('最大使用次数'), min_value=1, initial=1)
    expires_days = forms.IntegerField(label=_('有效期天数'), required=False, help_text=_('可选，优惠码的有效期天数'))

class MagicCodeUsageInline(admin.TabularInline):
    model = MagicCodeUsage
    extra = 0
    readonly_fields = ('user', 'used_at')
    can_delete = False

@admin.register(MagicCode)
class MagicCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'app_id', 'days', 'max_uses', 'used_count', 'status', 'expires_at', 'created_by', 'created_at')
    list_filter = ('status', 'app_id', 'created_at')
    search_fields = ('code', 'app_id', 'created_by__username')
    readonly_fields = ('used_count', 'created_by', 'created_at', 'updated_at')
    inlines = [MagicCodeUsageInline]
    actions = ['make_active', 'make_disabled', 'batch_create_codes']
    
    def make_active(self, request, queryset):
        queryset.update(status='active')
    make_active.short_description = "将选中的优惠码设为有效"
    
    def make_disabled(self, request, queryset):
        queryset.update(status='disabled')
    make_disabled.short_description = "将选中的优惠码设为禁用"
    
    def save_model(self, request, obj, form, change):
        if not change:  # 如果是新建
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('batch-create/', self.admin_site.admin_view(self.batch_create_view), name='magics_magiccode_batch_create'),
        ]
        return custom_urls + urls
    
    def batch_create_codes(self, request, queryset):
        """批量创建优惠码"""
        # 重定向到批量创建页面
        return HttpResponseRedirect("../batch-create/")
    batch_create_codes.short_description = "批量创建优惠码"
    
    def batch_create_view(self, request):
        """批量创建优惠码的视图"""
        # 处理表单提交
        if request.method == 'POST':
            form = BatchCreateForm(request.POST)
            if form.is_valid():
                count = form.cleaned_data['count']
                prefix = form.cleaned_data['prefix']
                app_id = form.cleaned_data['app_id']
                days = form.cleaned_data['days']
                max_uses = form.cleaned_data['max_uses']
                expires_days = form.cleaned_data['expires_days']
                
                # 设置过期时间
                expires_at = None
                if expires_days:
                    expires_at = timezone.now() + timezone.timedelta(days=expires_days)
                
                # 批量创建优惠码
                created_codes = []
                for _ in range(count):
                    code = MagicCode.generate_code(prefix=prefix)
                    magic_code = MagicCode.objects.create(
                        code=code,
                        app_id=app_id,
                        days=days,
                        max_uses=max_uses,
                        expires_at=expires_at,
                        created_by=request.user
                    )
                    created_codes.append(magic_code)
                
                self.message_user(request, f"成功创建 {count} 个优惠码")
                # 重定向到优惠码列表页面
                return HttpResponseRedirect("../")
        else:
            form = BatchCreateForm()
        
        # 渲染表单页面
        context = {
            'title': _('批量创建优惠码'),
            'form': form,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        return TemplateResponse(request, 'admin/magics/magiccode/batch_create.html', context)

@admin.register(MagicCodeUsage)
class MagicCodeUsageAdmin(admin.ModelAdmin):
    list_display = ('code', 'user', 'used_at')
    list_filter = ('used_at',)
    search_fields = ('code__code', 'user__username', 'user__email')
    readonly_fields = ('code', 'user', 'used_at')
