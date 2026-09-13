# -*- coding: utf-8 -*-
"""
适配器参数 Schema 系统 - Phase 4.5

为每个适配器定义参数 Schema，前端根据 Schema 动态渲染表单。

Schema 格式:
{
    "adapter": "适配器名称",
    "version": "1.0",
    "params": {
        "字段名": {
            "type": "string|integer|number|boolean|enum|array|date",
            "label": "显示名称",
            "description": "字段说明",
            "placeholder": "占位提示",
            "required": true/false,
            "default": 默认值,
            "min": 最小值 (number/integer),
            "max": 最大值 (number/integer),
            "options": [{"value": "x", "label": "显示"}],  # enum 类型
            "validation": "regex 或自定义规则",
        }
    }
}
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ParamField:
    """参数字段定义"""
    type: str  # string, integer, number, boolean, enum, array, date
    label: str
    description: str = ""
    placeholder: str = ""
    required: bool = False
    default: Any = None
    min: Optional[float] = None
    max: Optional[float] = None
    options: List[Dict[str, str]] = field(default_factory=list)
    validation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "type": self.type,
            "label": self.label,
            "description": self.description,
            "placeholder": self.placeholder,
            "required": self.required,
        }
        if self.default is not None:
            result["default"] = self.default
        if self.min is not None:
            result["min"] = self.min
        if self.max is not None:
            result["max"] = self.max
        if self.options:
            result["options"] = self.options
        if self.validation:
            result["validation"] = self.validation
        return result


@dataclass
class AdapterParamSchema:
    """适配器参数 Schema"""
    adapter: str
    version: str = "1.0"
    description: str = ""
    category: str = "general"  # finance, news, social, ecommerce, etc.
    params: Dict[str, ParamField] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为完整字典"""
        return {
            "adapter": self.adapter,
            "version": self.version,
            "description": self.description,
            "category": self.category,
            "params": {k: v.to_dict() for k, v in self.params.items()},
        }

    def validate(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证参数值

        Returns:
            {"valid": True} 或 {"valid": False, "errors": [...]}
        """
        errors = []
        validated = {}

        for field_name, field_def in self.params.items():
            value = values.get(field_name)

            # 必填检查
            if field_def.required and (value is None or value == ""):
                errors.append(f"{field_def.label} 是必填项")
                continue

            # 使用默认值
            if value is None and field_def.default is not None:
                value = field_def.default

            # 类型检查
            if value is not None:
                try:
                    if field_def.type == "integer":
                        value = int(value)
                        if field_def.min is not None and value < field_def.min:
                            errors.append(f"{field_def.label} 最小值为 {field_def.min}")
                        if field_def.max is not None and value > field_def.max:
                            errors.append(f"{field_def.label} 最大值为 {field_def.max}")
                    elif field_def.type == "number":
                        value = float(value)
                        if field_def.min is not None and value < field_def.min:
                            errors.append(f"{field_def.label} 最小值为 {field_def.min}")
                        if field_def.max is not None and value > field_def.max:
                            errors.append(f"{field_def.label} 最大值为 {field_def.max}")
                    elif field_def.type == "boolean":
                        if isinstance(value, str):
                            value = value.lower() in ("true", "1", "yes", "on")
                        else:
                            value = bool(value)
                    elif field_def.type == "enum":
                        valid_values = [opt["value"] for opt in field_def.options]
                        if value not in valid_values:
                            errors.append(f"{field_def.label} 必须是以下之一: {valid_values}")
                    elif field_def.type == "array":
                        if isinstance(value, str):
                            value = [v.strip() for v in value.split(",") if v.strip()]
                        elif not isinstance(value, list):
                            value = [value]
                    elif field_def.type == "date":
                        # 简单日期格式验证
                        if not re.match(r"\d{4}-\d{2}-\d{2}", str(value)):
                            errors.append(f"{field_def.label} 格式应为 YYYY-MM-DD")
                except (ValueError, TypeError) as e:
                    errors.append(f"{field_def.label} 类型错误: {e}")

            validated[field_name] = value

        if errors:
            return {"valid": False, "errors": errors}
        return {"valid": True, "values": validated}


# ==================== Schema 注册表 ====================

class SchemaRegistry:
    """参数 Schema 注册表"""

    _schemas: Dict[str, AdapterParamSchema] = {}

    @classmethod
    def register(cls, schema: AdapterParamSchema):
        """注册 Schema"""
        cls._schemas[schema.adapter] = schema

    @classmethod
    def get(cls, adapter: str) -> Optional[AdapterParamSchema]:
        """获取 Schema"""
        return cls._schemas.get(adapter)

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        """列出所有 Schema"""
        return [
            {
                "adapter": name,
                "version": schema.version,
                "description": schema.description,
                "category": schema.category,
                "param_count": len(schema.params),
            }
            for name, schema in cls._schemas.items()
        ]

    @classmethod
    def get_schema_detail(cls, adapter: str) -> Optional[Dict[str, Any]]:
        """获取 Schema 详情"""
        schema = cls.get(adapter)
        if schema:
            return schema.to_dict()
        return None


# 导入具体 Schema 定义（会触发注册）
from . import justoneapi_schema
from . import eastmoney_schema
from . import finance_schema
