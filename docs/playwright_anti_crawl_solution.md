# Playwright 反爬解决方案

## 目标
解决目标网站的反爬机制：
1. JavaScript 渲染检测
2. IP 封禁
3. 登录态验证

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    CrawlService (统一入口)                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ ProxyPool   │  │BrowserPool │  │ LoginSessionManager │  │
│  │ 代理池轮换  │  │ 浏览器池    │  │ 登录态管理          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Playwright CDP / HTTP Client             │
└─────────────────────────────────────────────────────────────┘
```

## 1. 代理池 (ProxyPool)

```python
# services/proxy_pool.py
class ProxyPool:
    """代理池管理"""
    def __init__(self):
        self.proxies = []
        self.current_index = 0

    def add_proxy(self, proxy: str):
        """添加代理: ip:port:user:pass"""
        self.proxies.append(proxy)

    def load_from_file(self, filepath: str):
        """从文件加载代理"""
        with open(filepath) as f:
            self.proxies = [line.strip() for line in f if line.strip()]

    def get_next(self) -> Optional[str]:
        """轮换获取代理"""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

    def mark_failed(self, proxy: str):
        """标记失败代理，临时移除"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
```

## 2. 浏览器池 (BrowserPool)

```python
# services/playwright_pool.py
from playwright.sync_api import sync_playwright
from contextlib import contextmanager

class BrowserPool:
    """Playwright 浏览器池"""

    STEALTH_ARGS = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
    ]

    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.playwright = None
        self.browsers = []

    def start(self):
        """启动浏览器池"""
        self.playwright = sync_playwright().start()
        for _ in range(self.pool_size):
            browser = self.playwright.chromium.launch(
                headless=True,
                args=self.STEALTH_ARGS
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.browsers.append(context)

    @contextmanager
    def get_context(self):
        """获取浏览器上下文"""
        context = self.browsers.pop(0)
        try:
            yield context
        finally:
            self.browsers.append(context)

    def close(self):
        """关闭浏览器池"""
        for ctx in self.browsers:
            ctx.close()
        for browser in set(ctx.browser for ctx in self.browsers if hasattr(ctx, 'browser')):
            browser.close()
        if self.playwright:
            self.playwright.stop()
```

## 3. 登录态管理 (LoginSessionManager)

```python
# services/login_session_manager.py
import json
import os
from pathlib import Path

class LoginSessionManager:
    """管理登录态 cookies"""

    def __init__(self, storage_dir: str = "data/sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, platform: str, context):
        """保存登录态"""
        storage_path = self.storage_dir / f"{platform}_storage.json"
        context.storage_state(path=str(storage_path))

    def load_session(self, platform: str):
        """加载登录态路径"""
        storage_path = self.storage_dir / f"{platform}_storage.json"
        if storage_path.exists():
            return {"storage_state": str(storage_path)}
        return {}

    def login(self, platform: str, username: str, password: str, login_url: str):
        """执行登录流程"""
        # 使用 Playwright 完成登录
        with browser_pool.get_context() as context:
            page = context.new_page()
            page.goto(login_url)
            # 填写表单并提交
            page.fill('#username', username)
            page.fill('#password', password)
            page.click('#login-button')
            page.wait_for_load_state('networkidle')
            self.save_session(platform, context)
            page.context.close()
```

## 4. 集成到爬虫服务

```python
# crawlers/eastmoney_playwright.py
class EastMoneyPlaywright:
    """东方财富 Playwright 版本"""

    def __init__(self):
        self.browser_pool = BrowserPool(pool_size=3)
        self.proxy_pool = ProxyPool()

    def fetch_stock(self, stock_code: str) -> List[Dict]:
        """使用 Playwright 爬取股票数据"""
        proxy = self.proxy_pool.get_next()

        with self.browser_pool.get_context() as context:
            if proxy:
                # 设置代理
                pass

            page = context.new_page()
            page.goto(f"https://quote.eastmoney.com/{stock_code}.html")
            page.wait_for_selector('.stockInfo', timeout=10000)

            # 提取数据
            data = page.evaluate('''() => {
                return {
                    price: document.querySelector('.price').textContent,
                    change: document.querySelector('.change').textContent,
                    volume: document.querySelector('.volume').textContent
                }
            }''')

            page.context.close()
            return data
```

## 5. 使用 Playwright MCP

如果配置了 Playwright MCP，可以直接使用：

```python
# 使用 MCP 工具
mcp__playwright__navigate(url="https://example.com")
mcp__playwright__click(selector="#login")
mcp__playwright__fill(selector="#username", value="user")
mcp__playwright__screenshot()
```

## 实现步骤

1. **Phase 1**: 创建基础组件
   - [ ] `services/proxy_pool.py`
   - [ ] `services/playwright_pool.py`
   - [ ] `services/login_session_manager.py`

2. **Phase 2**: 集成现有爬虫
   - [ ] 重写 eastmoney 爬虫使用 Playwright
   - [ ] 添加代理轮换
   - [ ] 添加登录态支持

3. **Phase 3**: 高难度网站
   - [ ] 微博登录爬虫
   - [ ] 知乎登录爬虫
   - [ ] 验证码处理

## 代理来源

免费代理池:
- https://www.proxyscrape.com/
- https://free-proxy-list.net/

付费代理 (推荐):
- 芝麻代理
- 讯代理
- 太阳 HTTP

## 注意事项

1. **遵守 robots.txt**
2. **控制请求频率** (每个 IP 1-2秒/请求)
3. **监控成功率** - 失败率 > 30% 换代理池
4. **定期更新 cookies** - 登录态过期前更新
5. **异常处理** - 超时、验证码、页面加载失败

---
方案制定时间: 2026-04-24
