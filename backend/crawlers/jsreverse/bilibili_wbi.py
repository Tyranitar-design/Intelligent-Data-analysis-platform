# -*- coding: utf-8 -*-
"""B站 wbi 签名（公开算法实现，多源交叉验证）

来源：
- bilibili-API-collect（SocialSisterYi）``docs/misc/sign/wbi.md``（算法文档）
- 独立实现交叉验证：Go（yu1745/bili-dl，注明沿用官方文档）· 另有 TS/Dart/Swift/C#/Java 等 8+ 仓库一致

算法：
1. ``GET /x/web-interface/nav`` → ``data.wbi_img.{img_url,sub_url}`` → 取文件名（去扩展名）为 img_key/sub_key
2. ``mixinKey = 按 MixinKeyEncTab 重排 (img_key+sub_key) 的前 32 位``
3. 参数 + ``wts``（秒时间戳）→ 排序 → 值去 ``!'()*`` → urlencode → 追加 mixinKey → md5 = ``w_rid``

用法::

    signer = BilibiliWbi()
    await signer.prepare()          # 拉取并缓存 mixin key（10 分钟）
    params = signer.sign({"search_type": "video", "keyword": "python"})
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Dict, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
SPI_URL = "https://api.bilibili.com/x/frontend/finger/spi"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
UNWANTED_CHARS = "!'()*"
CACHE_TTL_SECONDS = 600


class BilibiliWbi:
    """wbi 签名器（mixin key 缓存 10 分钟）。"""

    def __init__(self) -> None:
        self._mixin_key: Optional[str] = None
        self._updated_at: float = 0.0
        self.buvid3: Optional[str] = None

    # ------------------------------------------------------------------ #
    # key 获取
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_key(url: str) -> str:
        filename = (url or "").rstrip("/").rsplit("/", 1)[-1]
        return filename.split(".")[0]

    @staticmethod
    def get_mixin_key(orig: str) -> str:
        """按 MixinKeyEncTab 重排取前 32 位。"""
        return "".join(orig[i] for i in MIXIN_KEY_ENC_TAB if i < len(orig))[:32]

    async def prepare(self, force: bool = False) -> bool:
        """拉取 nav（wbi keys）+ 指纹接口（buvid3 游客标识）并缓存。"""
        if (
            not force
            and self._mixin_key
            and (time.time() - self._updated_at) < CACHE_TTL_SECONDS
        ):
            return True

        import httpx

        headers = {"User-Agent": UA, "Referer": "https://www.bilibili.com/"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(NAV_URL, headers=headers)
                data = resp.json()
                try:
                    spi = (await client.get(SPI_URL, headers=headers)).json()
                    self.buvid3 = ((spi.get("data") or {}).get("b_3")) or self.buvid3
                except Exception:  # noqa: BLE001 - 指纹为可选增强
                    pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("获取 wbi keys 失败: %s", exc)
            return False

        wbi_img = ((data.get("data") or {}).get("wbi_img")) or {}
        img_key = self._extract_key(wbi_img.get("img_url") or "")
        sub_key = self._extract_key(wbi_img.get("sub_url") or "")
        if not (img_key and sub_key):
            logger.warning("nav 响应缺少 wbi_img: %s", str(data)[:150])
            return False
        self._mixin_key = self.get_mixin_key(img_key + sub_key)
        self._updated_at = time.time()
        return True

    # ------------------------------------------------------------------ #
    # 签名
    # ------------------------------------------------------------------ #
    @staticmethod
    def _sanitize(value: str) -> str:
        for char in UNWANTED_CHARS:
            value = value.replace(char, "")
        return value

    def sign(self, params: Dict[str, str]) -> Dict[str, str]:
        """对参数签名：返回含 ``wts`` + ``w_rid`` 的新字典。"""
        if not self._mixin_key:
            raise RuntimeError("mixin key 未就绪——先 await prepare()")
        signed = {key: str(value) for key, value in params.items()}
        signed["wts"] = str(int(time.time()))
        keys = sorted(signed.keys())
        query = urlencode([(key, self._sanitize(signed[key])) for key in keys])
        signed["w_rid"] = hashlib.md5((query + self._mixin_key).encode()).hexdigest()
        return signed

    def request_headers(self) -> Dict[str, str]:
        """带游客指纹的请求头（有 buvid3 时注入 Cookie）。"""
        headers = {"User-Agent": UA, "Referer": "https://www.bilibili.com/"}
        if self.buvid3:
            headers["Cookie"] = f"buvid3={self.buvid3}"
        return headers
