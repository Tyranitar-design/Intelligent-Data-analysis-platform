# 采集能力阶梯矩阵（部署前实测规格）

> 目标：部署前从简单到复杂逐层验证采集能力有效性；每层 = 靶场 + 断言 + 证据。
> 纪律：失败层走最小修复（TDD 红→绿）；不通过的自如记录为 DEGRADED / FAIL。
> 更新：2026-09-15（规格先行，实测结果逐层回填）

## 分层定义

| 层 | 场景 | 靶场（练习专用 / 公开测试站，合法） | 验收断言 | 结果 |
|---|---|---|---|---|
| **L0** | 静态直采 | `books.toscrape.com` · `example.com` | `AdaptiveScraper.crawl` 成功；结构化数据非空；strategy 记录 | ⏳ |
| **L1** | 指纹伪装 | `httpbin.org/headers` · `tls.browserleaks.com/json` | ① 回显 UA 为浏览器 UA（非 python-httpx）② TLS(JA3/JA4) 与裸 httpx 有差异或如实记录 | ⏳ |
| **L2** | JS 渲染 | `quotes.toscrape.com/js/` | 策略链自动升级（httpx → scrapling/playwright）；JS 渲染后数据到手 | ⏳ |
| **L3** | 反爬挑战 | `nowsecure.nl`（Cloudflare 经典测试靶） | StealthyFetcher/浏览器池接管；挑战通过或如实记录降级链 | ⏳ |
| **L4** | 分页链路 | `quotes.toscrape.com/page/N` | 分页抓全 N 页；条目计数正确；URL 模式识别 | ⏳ |
| **L5** | 登录态 | Smoke assisted（Bilibili 半自动） | 人机协同断言链 pass（session_reuse_check）——已有 Smoke 覆盖 | ⏳ |
| **L6** | 逆向协同 | 合成签名 fixture（本地） | js_reverse_engine：fetch → AST 解析 → 函数提取 → execjs 求值（签名复现） | ⏳ |

## 判定口径

- **PASS**：断言满足且证据落盘（`docs/evidence/collect-ladder/`）
- **DEGRADED**：目标可达但走降级路径（记录实际策略与差距）
- **FAIL**：断言不满足 → 修复队列（TDD：先红后绿，最小实现）

## 执行方式

```powershell
cd backend
.\venv\Scripts\python.exe scripts\verify_collect_ladder.py            # 全部层
.\venv\Scripts\python.exe scripts\verify_collect_ladder.py -Layer L0,L1  # 指定层
```

## 证据

- `docs/evidence/collect-ladder/result.txt`（逐层断言）
- 每层原始输出（JSON）注明策略、耗时、质量分

## 备注

- L5 已由 Smoke Center assisted 流程覆盖（`docs/evidence/smoke-*`），本轮做回归确认。
- L1 的 TLS 指纹以实测为准（httpx 的 TLS 栈限制若暴露，记录为已知差距与修复候选）。
- 靶场均选用爬虫练习站/公开测试服务，遵守 robots；不针对真实生产站做压力测试。

## 验证码自动化链（决策修订 · 2026-09-15）

**D5 修订**：原「人机协同取代自动破解」→ **自动化优先（本地 OCR + 打码平台），人机协同兜底**。
（依据：平台所有者的明确目标——全自动化采集与分析挖掘。）

| 层 | 类型 | 技术路径 | 验收断言 | 结果 |
|---|---|---|---|---|
| **V1** | 图片验证码 | **ddddocr 本地识别**（离线、免费）→ 失败/低置信度时打码平台兜底 | 合成验证码图识别 == 原文本 | ⏳ |
| **V2** | 滑块验证码 | **OpenCV 缺口检测**（边缘定位）+ Playwright 轨迹模拟拖拽 | 合成滑块图距离 == 真值 ±2px | ⏳ |
| **V3** | 打码平台协议 | 2captcha / anticaptcha HTTP 协议（`CAPTCHA_API_KEY` 环境变量，无 key 时优雅降级） | 协议层单测（mock 服务） | ⏳ |
| **V4** | 行为验证码 | reCAPTCHA/hCaptcha/极验：打码平台 token + 浏览器注入 | 后续层（需真实 API key） | ⏳ |

**接入点**：`crawlers/anticrawl/captcha_solver.py`（页面集成 `solve_captcha_on_page` 已有），
探测链路由 anticrawl_engine 调用；识别成功/失败均写入任务事件流（可审计）。
