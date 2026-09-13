"""
数据源管理
"""
from django.contrib import admin
from .models import DataSource, CrawlTask

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'status', 'created_at']
    list_filter = ['source_type', 'status']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CrawlTask)
class CrawlTaskAdmin(admin.ModelAdmin):
    list_display = ['source', 'status', 'started_at', 'completed_at']
    list_filter = ['status']
    readonly_fields = ['created_at', 'started_at', 'completed_at']