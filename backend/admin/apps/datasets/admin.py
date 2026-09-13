"""
数据集 Admin 配置
"""
from django.contrib import admin
from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """数据集管理"""
    list_display = ['name', 'type', 'table_name', 'row_count', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['name', 'description', 'table_name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
