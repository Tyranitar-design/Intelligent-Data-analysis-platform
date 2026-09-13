"""
报告 Admin 配置
"""
from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """分析报告管理"""
    list_display = ['title', 'report_type', 'template', 'status', 'created_at']
    list_filter = ['report_type', 'template', 'status', 'created_at']
    search_fields = ['title']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'report_type', 'template', 'status')
        }),
        ('内容', {
            'fields': ('content',)
        }),
        ('时间', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
