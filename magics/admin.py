from django.contrib import admin
from .models import MagicCode, MagicCodeUsage

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
    actions = ['make_active', 'make_disabled']
    
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

@admin.register(MagicCodeUsage)
class MagicCodeUsageAdmin(admin.ModelAdmin):
    list_display = ('code', 'user', 'used_at')
    list_filter = ('used_at',)
    search_fields = ('code__code', 'user__username', 'user__email')
    readonly_fields = ('code', 'user', 'used_at')
