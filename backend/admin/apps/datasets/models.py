"""
数据集模型
"""
from django.db import models

class Dataset(models.Model):
    """数据集"""
    name = models.CharField(max_length=100, verbose_name='名称')
    description = models.TextField(blank=True, verbose_name='描述')
    type = models.CharField(max_length=50, verbose_name='类型')
    table_name = models.CharField(max_length=100, verbose_name='表名')
    row_count = models.IntegerField(default=0, verbose_name='行数')
    columns = models.JSONField(default=list, verbose_name='列信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '数据集'
        verbose_name_plural = '数据集'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name