"""
报告模型
"""
from django.db import models

class Report(models.Model):
    """分析报告"""
    REPORT_TYPES = [
        ('daily', '日报'),
        ('weekly', '周报'),
        ('monthly', '月报'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='标题')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name='类型')
    template = models.CharField(max_length=50, verbose_name='模板')
    content = models.JSONField(default=dict, verbose_name='内容')
    status = models.CharField(max_length=20, default='pending', verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '分析报告'
        verbose_name_plural = '分析报告'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title