# 采集能力阶梯矩阵（部署前实测规格）

> 目标：部署前从简单到复杂逐层验证采集能力有效性；每层 = 靶场 + 断言 + 证据。
> 纪律：失败层走最小修复（TDD 红→绿）；不通过的自如记录为 DEGRADED / FAIL。
> 更新：2026-09-15（规格先行，实测结果逐层回填）

## 分层定义

| 层 | 场景 | 靶场（练习专用 / 公开测试站，合法） | 验收断言 | 结果 |
|---|---|---|---|---|
| **L0** | 静态直采 | `books.toscrape.com` · `example.com` | `AdaptiveScraper.crawl` 成功；结构化数据非空；strategy 记录 | ✅ 2/2（scrapling · 2.3s/1.0s） |
| **L1** | 指纹伪装 | `httpbin.org/headers` · `tls.browserleaks.com/json` | ① 回显 UA 为浏览器 UA ② TLS(JA3) 与裸 httpx 有差异 | ✅ 3/3（UA 伪装 ✓；Scrapling ja3≠httpx ja3） |
| **L2** | JS 渲染 | `quotes.toscrape.com/js/` | 策略链自动升级；JS 渲染后数据到手 | ✅ quality=0.9375（scrapling） |
| **L3** | 反爬挑战 | `nowsecure.nl`（Cloudflare 经典测试靶） | StealthyFetcher/浏览器池接管；挑战通过 | ✅ 8.5s（Fetcher→挑战检测→StealthyFetcher 升级链） |
| **L4** | 分页链路 | `quotes.toscrape.com/page/N` | 分页抓全 N 页；条目计数正确 | ✅ 30/30（3 页 × 10 条） |
| **L5** | 登录态 | Smoke assisted（Bilibili 半自动） | 人机协同断言链 pass | ⏳ 由 Smoke 覆盖（回归入口） |
| **L6** | 逆向协同 | 合成签名 fixture（本地） | fetch → AST → 提取 → execjs 求值 | ✅ 4/4（签名复现 `wb_secret_2024_42_1700000000_*`） |

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
| **V1** | 图片验证码 | **ddddocr 本地识别**（离线、免费）→ 失败/低置信度时打码平台兜底 | 合成验证码图识别 == 原文本 | ✅ 4/4（含批量参数化） |
| **V2** | 滑块检测 | **OpenCV 缺口检测**（暗区阈值主路径 + Canny 边缘兜底） | 合成滑块图距离 == 真值 ±2px | ✅ 3/3（120/180/210 全精确） |
| **V2b** | 滑块拖拽 | **拟人轨迹**（加速-减速 + 垂直抖动 + 过冲回退）+ Playwright 拖拽 | 本地合成页 e2e：最终位置 == 目标 ±3px | ✅ e2e 通过（净位移受控） |
| **V3** | 打码平台协议 | 2captcha HTTP 协议（`CAPTCHA_API_KEY`，无 key 优雅降级） | 协议层单测（mock 服务） | ⏳ 代码就绪（实测需 key） |
| **V4** | 行为验证码 | reCAPTCHA/hCaptcha/极验：打码平台 token + 浏览器注入 | 后续层 | ⏳ 路线图 |

**接入点**：`crawlers/anticrawl/captcha_solver.py`（页面集成 `solve_captcha_on_page` 已有），
探测链路由 anticrawl_engine 调用；识别成功/失败均写入任务事件流（可审计）。
