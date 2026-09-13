# -*- coding: utf-8 -*-
"""
预置适配器包
===========

包含:
- eastmoney: 东方财富 (金融)
- kr36: 36氪 (新闻)
- cls: 财联社 (新闻)
- justoneapi: JustOneAPI 社交媒体平台
- public_apis: 汇率/天气/维基等公共 API

导入本模块时会触发适配器注册。
"""

from . import eastmoney  # noqa: F401
from . import kr36  # noqa: F401
from . import cls  # noqa: F401
from . import justoneapi  # noqa: F401
from . import public_apis  # noqa: F401
