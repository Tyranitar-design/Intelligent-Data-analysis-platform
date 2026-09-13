"""
数据源模型
"""
from django.db import models
from django.contrib.auth.models import User

class DataSource(models.Model):
    """数据源"""
    SOURCE_TYPES = [
        ('ecommerce', '电商数据'),
        ('finance', '金融数据'),
        ('social', '社交数据'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='名称')
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, verbose_name='类型')
    config = models.JSONField(default=dict, verbose_name='配置')
    status = models.CharField(max_length=20, default='active', verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '数据源'
        verbose_name_plural = '数据源'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class CrawlTask(models.Model):
    """爬虫任务"""
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, verbose_name='数据源')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    config = models.JSONField(default=dict, verbose_name='配置')
    result = models.JSONField(default=dict, verbose_name='结果')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '爬虫任务'
        verbose_name_plural = '爬虫任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.source.name} - {self.status}"