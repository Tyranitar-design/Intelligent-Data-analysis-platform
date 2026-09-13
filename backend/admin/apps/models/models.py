"""
ML 模型管理
"""
from django.db import models

class MLModel(models.Model):
    """机器学习模型"""
    MODEL_TYPES = [
        ('classification', '分类'),
        ('regression', '回归'),
        ('clustering', '聚类'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='名称')
    model_type = models.CharField(max_length=20, choices=MODEL_TYPES, verbose_name='类型')
    algorithm = models.CharField(max_length=50, verbose_name='算法')
    params = models.JSONField(default=dict, verbose_name='参数')
    metrics = models.JSONField(default=dict, verbose_name='指标')
    path = models.CharField(max_length=255, blank=True, verbose_name='模型路径')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = 'ML模型'
        verbose_name_plural = 'ML模型'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.algorithm})"


class PredictionTask(models.Model):
    """预测任务"""
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, verbose_name='模型')
    input_data = models.JSONField(default=dict, verbose_name='输入数据')
    result = models.JSONField(default=dict, verbose_name='预测结果')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '预测任务'
        verbose_name_plural = '预测任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"预测 - {self.model.name}"