# -*- coding: utf-8 -*-
"""
浏览器指纹伪装

功能：
- User-Agent 轮换
- 视口随机化
- 时区伪装
- WebGL 指纹伪装
- Canvas 指纹伪装
"""
import random
from typing import Dict, Any, Optional


class FingerprintMasker:
    """指纹伪装器"""

    # 常见 User-Agent 列表
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    ]

    # 常见视口尺寸
    VIEWPORTS = [
        (1920, 1080),
        (1366, 768),
        (1440, 900),
        (1536, 864),
        (1280, 720),
        (1680, 1050),
    ]

    # 常见时区
    TIMEZONES = [
        "Asia/Shanghai",
        "Asia/Beijing",
        "Asia/Hong_Kong",
        "Asia/Tokyo",
        "Asia/Seoul",
        "America/New_York",
        "America/Los_Angeles",
        "Europe/London",
        "Europe/Paris",
    ]

    # 常见语言
    LANGUAGES = [
        "zh-CN,zh;q=0.9,en;q=0.8",
        "en-US,en;q=0.9,zh-CN;q=0.8",
        "zh-TW,zh;q=0.9,en-US;q=0.8",
        "ja-JP,ja;q=0.9,en;q=0.8",
        "ko-KR,ko;q=0.9,en;q=0.8",
    ]

    def __init__(self):
        self.current_fingerprint = None

    def generate_fingerprint(self) -> Dict[str, Any]:
        """生成随机指纹"""
        fingerprint = {
            "user_agent": random.choice(self.USER_AGENTS),
            "viewport": random.choice(self.VIEWPORTS),
            "timezone": random.choice(self.TIMEZONES),
            "language": random.choice(self.LANGUAGES),
            "color_depth": random.choice([24, 32]),
            "pixel_ratio": random.choice([1, 1.25, 1.5, 2]),
            "hardware_concurrency": random.choice([4, 8, 16]),
            "memory": random.choice([8, 16, 32]),
        }
        self.current_fingerprint = fingerprint
        return fingerprint

    def get_playwright_context(self) -> Dict[str, Any]:
        """获取 Playwright 上下文配置"""
        if not self.current_fingerprint:
            self.generate_fingerprint()

        fp = self.current_fingerprint
        return {
            "user_agent": fp["user_agent"],
            "viewport": {"width": fp["viewport"][0], "height": fp["viewport"][1]},
            "timezone_id": fp["timezone"],
            "locale": fp["language"].split(";")[0].split(",")[0],
            "color_scheme": "light",
            "reduced_motion": "no_preference",
        }

    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        if not self.current_fingerprint:
            self.generate_fingerprint()

        fp = self.current_fingerprint
        return {
            "User-Agent": fp["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": fp["language"],
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    def rotate(self):
        """轮换指纹"""
        self.generate_fingerprint()

    def mask_webgl(self, page):
        """伪装 WebGL 指纹"""
        # 通过 JS 注入修改 WebGL 参数
        page.evaluate("""
            () => {
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter(parameter);
                };
            }
        """)

    def mask_canvas(self, page):
        """伪装 Canvas 指纹"""
        # 通过 JS 注入添加噪声
        page.evaluate("""
            () => {
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {
                    const context = this.getContext('2d');
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    const data = imageData.data;
                    // 添加微小噪声
                    for (let i = 0; i < data.length; i += 4) {
                        data[i] += Math.random() > 0.5 ? 1 : -1;
                    }
                    context.putImageData(imageData, 0, 0);
                    return originalToDataURL.call(this, type);
                };
            }
        """)

    def mask_plugins(self, page):
        """伪装插件列表"""
        page.evaluate("""
            () => {
                Object.defineProperty(navigator, 'plugins', {
                    get: function() {
                        return [
                            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                            {name: 'Native Client', filename: 'internal-nacl-plugin'}
                        ];
                    }
                });
            }
        """)

    def apply_all_masks(self, page):
        """应用所有伪装"""
        self.mask_webgl(page)
        self.mask_canvas(page)
        self.mask_plugins(page)
