"""
ML 模型 Admin 配置
"""
from django.contrib import admin
from .models import MLModel, PredictionTask


@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    """机器学习模型管理"""
    list_display = ['name', 'model_type', 'algorithm', 'path', 'created_at']
    list_filter = ['model_type', 'algorithm', 'created_at']
    search_fields = ['name', 'algorithm']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'model_type', 'algorithm')
        }),
        ('模型配置', {
            'fields': ('params', 'metrics', 'path')
        }),
        ('时间', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PredictionTask)
class PredictionTaskAdmin(admin.ModelAdmin):
    """预测任务管理"""
    list_display = ['id', 'model', 'created_at']
    list_filter = ['created_at', 'model__model_type']
    search_fields = ['model__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    def has_change_permission(self, request, obj=None):
        return False  # 预测任务只读
