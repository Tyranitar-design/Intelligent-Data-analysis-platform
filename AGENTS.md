# 智能数据分析平台 - AGENTS 项目指南

> 本文件给 Codex / 小 c / 其他自动化代理作为项目接手手册使用。内容基于当前项目文件夹通读整理，后续若架构、入口或工作流变化，应同步更新。

## 1. 项目定位

本项目是一个企业级智能数据分析平台，目标是把数据采集、登录态与反爬处理、数据集管理、探索性分析、机器学习 / 深度学习、数据挖掘、可视化、报告生成和验收中心串成一条可运行的产品主链。

当前代码库采用：
- 后端：FastAPI + SQLAlchemy + Celery + Redis + PostgreSQL / SQLite
- 前端：React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui + Zustand + TanStack Query
- 数据与 AI：Pandas / NumPy / scikit-learn / XGBoost / LightGBM / PyTorch / Transformers
- 采集与反爬：httpx / Scrapling / Playwright / robots.txt 检查 / 登录态 Cookie 管理
- 部署与联调：本地开发脚本优先，Docker Compose v2 作为后续集成与部署路径

## 2. 推荐阅读顺序

开始任何较大任务前，优先按这个顺序读：
1. `README-v2.md`：当前 v2 主线、运行方式、技术栈与功能范围
2. `openspec/README.md`：OpenSpec 工作流和活跃变更组织方式
3. `.codex/memory/MEMORY.md`：项目热记忆索引，先用它快速恢复上下文
4. `.codex/memory/PROJECT_MEMORY.md`：项目长期记忆和默认假设
5. `.codex/memory/DECISIONS.md`：当前已确认的架构决策
6. `.codex/memory/KNOWN_ISSUES.md`：已知问题与工作流注意事项
7. `docs/DEVELOPMENT_BASELINE.md`：稳定开发基线、版本控制边界、canonical 入口
8. `docs/PHASE1_REPOSITORY_CHECKLIST.md`：哪些文件应提交，哪些应保持本地
9. `docs/DATA_SOURCE_MAP.md`：已集成数据源、JustOneAPI 能力和反爬限制
10. `AUTH-ANTICRAWL-GUIDE.md`：登录态、Cookie、Playwright 与反爬策略

## 3. 当前稳定入口

当前 canonical 入口以 `docs/DEVELOPMENT_BASELINE.md` 和实际代码为准：

- 后端 API：`backend/api/main.py`
- 前端应用：`frontend/package.json` + `frontend/src/App.tsx`
- 本地启动：`run-dev.cmd` -> `scripts/run-dev.ps1`
- Docker 编排：`docker-compose-v2.yml`
- 后端配置：`backend/api/core/config.py`
- 数据库入口：`backend/api/database.py` 与 `backend/api/core/database.py`

历史 / 参考入口仍保留，但新工作不要默认从这些文件开始：
- `backend/api/main-v2.py`
- `backend/run_api.py`
- `backend/run_api_simple.py`
- `frontend/src/App-v2.tsx`
- `frontend/package-v2.json`
- `docker-compose.yml`

## 4. 本地开发方式

推荐本地开发优先，Docker 用于后续联调或部署验证。

后端准备：
```powershell
cd D:\智能数据分析平台\backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-v2.txt
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

前端准备：
```powershell
cd D:\智能数据分析平台\frontend
npm install
```

一键开发脚本：
```powershell
cd D:\智能数据分析平台
.\run-dev.cmd check
.\run-dev.cmd start
.\run-dev.cmd status
.\run-dev.cmd stop
```

默认地址：
- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`
- 能力状态：`http://127.0.0.1:8000/capabilities`

注意：`frontend/vite.config.ts` 里开发端口写的是 `3000`，但 `scripts/run-dev.ps1` 显式用 `5173` 启动 Vite。以后排查端口问题时，以实际启动脚本为准。

Docker v2：
```powershell
cd D:\智能数据分析平台
$env:COMPOSE_PROJECT_NAME="idp"
docker compose -f docker-compose-v2.yml up -d
docker compose -f docker-compose-v2.yml logs -f
docker compose -f docker-compose-v2.yml down
```

Docker 栈包括 PostgreSQL、Redis、MinIO、FastAPI、Celery Worker、Celery Beat、前端、Prometheus 和 Grafana。

## 4.1 已确认的本地 PostgreSQL / PostGIS 环境

当前机器上已经完成并验证了一套可直接使用的本地 PostgreSQL + PostGIS 环境，后续项目对话默认可以把它视为可用基础设施。

已确认事实：
- PostgreSQL 安装目录：`D:\PostgreSQL`
- PostgreSQL 版本：`18.4`
- Windows 服务名：`postgresql-x64-18`
- 验证时服务状态：`Running`
- 数据目录：`D:\PostgreSQL\data`
- 默认端口：`5432`
- 超级用户：`postgres`
- `psql` 路径：`D:\PostgreSQL\bin\psql.exe`
- `pgAdmin 4` 路径：`D:\PostgreSQL\pgAdmin 4\runtime\pgAdmin4.exe`
- 已验证业务数据库：`app_dev`
- 已在 `app_dev` 中成功启用：`PostGIS 3.6.2`

Windows 使用约定：
- 建议把 `D:\PostgreSQL\bin` 加入用户或系统 `Path`，这样 PowerShell、cmd、脚本和开发工具里都能直接调用 `psql`、`pg_dump`、`createdb`。
- 如果某个终端会话里找不到 `psql`，优先检查是否重新打开了终端；必要时可在 cmd 中运行 `D:\PostgreSQL\pg_env.bat`。

本项目中的数据库默认选择：
- 对新功能、新表、新分析链路，默认优先选 PostgreSQL。
- 涉及地理空间、地图、点位、距离、区域、轨迹、路线、仓网、配送范围等能力时，优先使用 PostGIS，而不是自行造空间字段约定。
- 需要结构化分析、JSON 数据、复杂约束、可解释 SQL、后续 AI / agent / 数据挖掘整合时，优先沿用 PostgreSQL 生态。
- 只有在明确存在遗留兼容、供应商限制或外部系统强绑定时，才考虑引入 MySQL 或其他数据库。

实务建议：
- 不要把数据库密码、连接串明文、Cookie、Token 等敏感信息写进 `AGENTS.md`、`.codex/memory/` 或提交到版本库。
- 如果后续从 `app_dev` 迁移到项目专用数据库，优先同步更新本文件和 `.codex/memory/DECISIONS.md`。

## 5. 目录地图

```text
backend/
  api/                 FastAPI 入口、路由、schemas、models、Celery 任务
  analysis/            EDA、统计分析、图表数据、分析服务
  crawlers/            数据采集、适配器、登录态、反爬、智能爬虫 v2
  database/            数据访问服务与数据库模型
  ml/                  机器学习服务与 pipeline
  dl/                  深度学习服务与 pipeline
  mining/              关联规则、异常检测、时序模式等数据挖掘
  reports/             报告生成服务
  smoke/               Smoke Center 场景、契约、运行编排、人机协同验收
  admin/               Django admin 风格的后台参考实现

frontend/
  src/App.tsx          React 路由入口
  src/api/             axios 客户端与模块化 API 封装
  src/components/      布局、通用组件、shadcn/ui、业务组件
  src/pages/           工作台、采集、分析、模型、可视化、报告、验收中心等页面
  src/stores/          Zustand 状态管理
  src/styles/          全局样式、动画、主题变量

openspec/
  changes/             当前活跃变更，必须符合当前 OpenSpec delta 格式
  legacy/              旧版 / 历史提案，保留参考但不作为活跃变更
  specs/               Harness Engineering 与 Vibe Coding 规范

docs/
  DEVELOPMENT_BASELINE.md
  PHASE1_REPOSITORY_CHECKLIST.md
  DATA_SOURCE_MAP.md
  phase / plan / smoke 相关文档

.codex/
  memory/              项目热记忆、长期记忆、capture 日志、专家代理路由表
  skills/              项目本地 OpenSpec 技能
  agents/              项目本地专家代理定义
```

## 5.1 本地混合记忆系统

本项目已经接入 Little C 的本地混合记忆系统，遵循：
- Markdown 文件是唯一真相源
- `.codex/memory/MEMORY.md` 是热启动入口
- `C:\Users\Administrator\.codex\memories\little-c\` 是 Little C 的全局 durable memory
- `C:\Users\Administrator\.codex\memories\little-c\index\memory.sqlite` 是本地检索索引
- `agentmemory` 作为 MCP-only 增强检索层接入，不替代 Markdown 记忆
- `understand-anything` 作为代码图谱 / 架构探索技能接入，用于代码结构理解与影响分析
- 科研默认工具箱已就位：`literature-review`、`scientific-writing`、`peer-review`、`citation-management`、`scientific-slides`、`scientific-schematics`、`exploratory-data-analysis`、`statistical-analysis`、`hypothesis-generation`、`get-available-resources`
- 追加科研/优化技能：`scientific-brainstorming`、`what-if-oracle`、`pymoo`、`simpy`

当前项目内与记忆系统直接相关的目录：
- `.codex/memory/MEMORY.md`
- `.codex/memory/PROJECT_MEMORY.md`
- `.codex/memory/DECISIONS.md`
- `.codex/memory/KNOWN_ISSUES.md`
- `.codex/memory/WORKLOG.md`
- `.codex/memory/captures/`

工作流命令在工作区 `C:\Users\Administrator\Documents\Codex\2026-05-09\new-chat-3`：
```powershell
cd C:\Users\Administrator\Documents\Codex\2026-05-09\new-chat-3
.\capture-memory.cmd --scope project --project-key intelligent-data-platform --title "标题" --summary "摘要"
.\consolidate-memory.cmd --scope project --project-key intelligent-data-platform
.\sync-memory-index.cmd
```

用途约定：
- `capture-memory`：写入原始记忆条目，适合记录重要结论、验证结果、运行观察
- `consolidate-memory`：把 durable memory 归并为热记忆索引 `MEMORY.md`
- `sync-memory-index`：同步项目镜像并重建 SQLite 检索索引

职责分工：
- Little C 自建记忆系统：
  - 负责 durable facts、项目约定、架构决策、已知问题、热记忆索引
  - 负责项目镜像同步和本地 SQLite 检索
- `agentmemory`：
  - 负责增强召回、跨 session 检索、关系式搜索、补充型记忆发现
  - 不应单独作为项目真相源
- `understand-anything`：
  - 负责代码图谱、结构关系、影响分析、项目上手理解
  - 不应单独作为项目真相源
- 科研技能：
  - 负责文献检索、论文/报告写作、同行评审、引用管理、统计分析、假设生成、科学图示与汇报
  - 负责研究脑暴、情景分析、运筹优化、离散事件仿真

推荐使用顺序：
- 先读 `.codex/memory/MEMORY.md`
- 需要写入长期事实时，优先更新 Markdown memory / capture
- 需要重新生成热索引时，运行 `consolidate-memory` / `sync-memory-index`
- 需要从更长的历史会话、关联线索或 session 角度做回忆时，再优先使用 `agentmemory`
- 需要理解代码库结构、依赖关系、影响面时，再优先使用 `understand-anything`
- 需要做科研、论文、实验、综述、统计或汇报时，再优先使用科研技能工具箱
- 需要做运筹优化、仿真、Pareto 多目标、实验假设、情景推演时，再优先使用 `pymoo` / `simpy` / `what-if-oracle` / `scientific-brainstorming`

当前项目的额外约定：
- Smoke Center 运行结果会尽量自动写入 `.codex/memory/captures/`
- 对于重要架构决策，仍应显式补到 `.codex/memory/DECISIONS.md`
- 对于稳定已知问题，仍应显式补到 `.codex/memory/KNOWN_ISSUES.md`

## 6. 后端架构要点

`backend/api/main.py` 是当前 FastAPI 主入口。启动时会：
- 初始化日志
- 加载 `settings`
- 调用 `init_db()` 创建数据库表
- 配置 CORS
- 记录请求耗时并写入 `X-Process-Time`、`X-API-Version`
- 注册全局异常处理器

默认挂载路由：
- `/health`：健康检查与 readiness
- `/api/v1/auth`：用户注册、登录、当前用户
- `/api/v1/crawl`：采集、适配器、URL 爬取、登录态、robots、文件导入、Celery 任务
- `/api/v1/analysis`：数据概览、EDA、统计分析、图表数据、分析数据集
- `/api/v1/data`：数据库表浏览、schema、rows、export、stats、overview
- `/api/v1/reports`：报告列表、生成、按表生成、删除
- `/api/v1/smoke`：验收中心 scenarios、contracts、run、assisted auth

可选路由：
- `/api/v1/ml`
- `/api/v1/dl`
- `/api/v1/mining`

这些可选路由通过 `_try_import_optional_router()` 动态导入：依赖完整时会挂载，依赖缺失时会被记录为 disabled，不应让主 API 启动失败。

## 7. 数据采集与反爬

采集主入口是 `backend/api/routers/crawl.py`，它承担多个阶段积累的能力：
- 数据源与采集任务管理
- 金融、新闻、电商等预置采集接口
- 适配器注册、自动发现和统一调用
- JustOneAPI 参数映射
- URL 探测、单页爬取、分页爬取
- 智能字段抽取与榜单抽取
- 智能爬虫 v2：`/smart/v2/probe`、`/smart/v2/crawl`
- robots.txt 合规检查
- 自定义采集配置
- 本地文件解析、导入与保存为数据集
- Celery 高 / 中 / 低优先级采集任务
- Scrapling 状态检查
- 登录态管理：平台列表、会话列表、自动登录、Cookie 导入、状态检查、登出、认证头

采集核心模块：
- `backend/crawlers/adapter_framework.py`：`BaseAdapter`、`AdapterRegistry`、`register_adapter`
- `backend/crawlers/adapters/`：东方财富、财联社、36kr、JustOneAPI、公共 API 等适配器
- `backend/crawlers/auth/`：`AuthManager`、Cookie 存储、Cookie 加密、平台登录流程
- `backend/crawlers/anticrawl/`：指纹伪装、浏览器池、验证码、反爬引擎
- `backend/crawlers/intelligent/`：自适应智能爬虫 v2
- `backend/crawlers/custom/`：用户自定义采集 schema 与执行引擎

智能爬虫 v2 的核心是 `AdaptiveScraper`：
- 先 `probe()` URL，识别内容类型、保护状态、登录需求、分页特征和意图
- 通过 Intent Engine 选择策略
- 默认策略包括 `httpx`、`Scrapling`、`Crawl4AI`、`Playwright`
- 支持策略降级、质量评估、熔断、生命周期 hook、指标与可观测日志

反爬原则：
- 优先使用公开 API 和合规接口
- 对网页采集先检查 robots.txt
- 对需登录或验证码的站点使用人机协同，不硬绕敏感流程
- Cookie 和登录态属于本地敏感数据，不应提交

## 8. 数据源现状

已集成并记录在 `docs/DATA_SOURCE_MAP.md` 的能力包括：
- 免费 API：东方财富、ExchangeRate、wttr.in、Wikipedia
- JustOneAPI：小红书、抖音、微博、淘宝、B站、京东、知乎、快手、微信、豆瓣、头条、TikTok、YouTube、Instagram、Twitter/X、Facebook、亚马逊、IMDb、Reddit、贝壳、优酷、1688、抖音电商、抖音星图、小红书蒲公英、通用网页抓取等
- 合计约 27 个平台、200+ API 接口

当前反爬能力：
- User-Agent 轮换
- 请求限速
- 自动重试与指数退避
- Scrapling Fetcher
- robots.txt 检查与 crawl-delay 遵守
- 代理参数支持
- 请求头增强
- httpx 到 Scrapling 的回退

当前限制：
- StealthyFetcher 需要额外安装 `patchright` / `camoufox`
- 没有自动代理池
- 不支持自动解验证码
- JavaScript 重度页面依赖 Scrapling / Playwright / 后续增强策略

## 9. 数据分析、ML、DL、挖掘与报告

分析服务：
- `backend/analysis/service.py`：数据加载、EDA、描述统计、异常值、图表数据
- `backend/analysis/eda_engine.py`、`feature_engine.py`、`visualizer.py`、`report_engine.py`：更细的分析、特征、可视化与报告能力

机器学习：
- `backend/ml/pipeline.py`
- `backend/ml/service.py`
- API 覆盖算法列表、模型管理、数据库训练、普通训练、预测、增强训练

深度学习：
- `backend/dl/pipeline.py`
- `backend/dl/service.py`
- API 覆盖 LSTM、文本分类器、AutoEncoder、模型列表

数据挖掘：
- `backend/mining/pipeline.py`
- `backend/mining/service.py`
- API 覆盖 Apriori、Isolation Forest、时序模式等

报告：
- `backend/reports/service.py`
- API 支持报告列表、生成、基于表生成和删除
- Smoke Center 会调用报告服务生成主链验证产物

## 10. Smoke Center 验收中心

Smoke Center 是当前项目很重要的闭环验证模块。后端在 `backend/smoke/`，前端在 `frontend/src/pages/SmokeCenter.tsx`。

后端模块：
- `backend/smoke/models.py`：状态枚举、请求 / 响应契约
- `backend/smoke/scenario_registry.py`：验收场景注册表
- `backend/smoke/service.py`：非认证 smoke run 编排
- `backend/smoke/assisted_auth.py`：人机协同登录验收
- `backend/api/routers/smoke.py`：API 路由

当前 API：
- `GET /api/v1/smoke/scenarios`
- `GET /api/v1/smoke/contracts`
- `POST /api/v1/smoke/run`
- `POST /api/v1/smoke/assisted/start`
- `POST /api/v1/smoke/assisted/continue`

当前场景方向：
- `local`：本地结构化数据 -> 保存数据集 -> EDA -> 报告
- `live-public`：公开 URL -> robots 检查 -> 后续执行采集链
- `live-assisted`：首个平台以 Bilibili 人机协同登录为验证切入点

前端页面提供：
- Local Smoke 输入 JSON rows 并运行
- Live Public 静态 / 动态 URL 验收
- Live Assisted 启动与继续人机协同流程
- contracts 状态 vocabulary 展示
- 最近一次运行结果、robots、数据集、分析与报告状态展示

## 11. 前端架构要点

`frontend/src/App.tsx` 是当前 React 路由入口。整体结构：
- `QueryClientProvider`
- `ThemeProvider`
- `MainLayout`
- 页面路由
- `Toaster`

主要页面：
- `/`：工作台
- `/sources`：数据源
- `/crawl`：数据采集
- `/data`：数据浏览
- `/datasets`：数据集
- `/import`：数据导入
- `/analysis`：数据分析
- `/ml`：模型训练
- `/dl`：深度学习
- `/mining`：数据挖掘
- `/models`：模型管理
- `/visualization`：可视化
- `/reports`：报告中心
- `/report`：报告详情 / 生成相关页面
- `/smoke`：验收中心
- `/settings`：设置

前端 API：
- `frontend/src/api/client.ts`：axios 基础客户端，`baseURL=/api/v1`，timeout 120s
- `frontend/src/api/crawl.ts`：采集、适配器、智能爬虫、文件导入、数据集、登录态
- `frontend/src/api/smoke.ts`：Smoke Center
- `frontend/src/api/analysis.ts`：分析接口
- `frontend/src/api/data.ts`：表浏览与导出
- `frontend/src/api/ml.ts`、`dl.ts`、`mining.ts`：模型、深度学习、挖掘接口
- `frontend/src/api/system.ts`：系统能力状态

主布局：
- `frontend/src/components/layout/MainLayout.tsx`
- `frontend/src/components/layout/Sidebar.tsx`

UI 基础：
- shadcn/ui 风格组件在 `frontend/src/components/ui/`
- 图标优先用 `lucide-react`
- 状态管理在 `frontend/src/stores/`

## 12. OpenSpec 工作流

项目使用 OpenSpec 管理较大的功能、重构和架构变更。

规则：
- 大功能、重构、跨模块设计变更：先走 OpenSpec
- 优先使用 `openspec-propose`、`openspec-explore`
- 新变更使用 `openspec new change <change-name>`
- 不要复制旧的 legacy change 作为新模板
- 活跃变更放在 `openspec/changes/`
- 历史旧格式文档放在 `openspec/legacy/`

当前活跃索引：
- `openspec/changes/index.md`

当前重要活跃 / 近活跃变更：
- `baseline-and-architecture-phase1`：阶段一规范与基线收敛，任务已完成
- `smoke-center-assisted-collection`：Smoke Center 与人机协同采集规划，任务清单仍显示未全部完成

已知问题：
- `.codex/memory/KNOWN_ISSUES.md` 记录：部分旧 `openspec/changes/*` 曾不符合最新 delta 规则
- 后续应优先创建新的合规 change，而不是继续扩展旧格式目录

## 13. 测试与验证入口

后端测试文件集中在 `backend/test_*.py`，覆盖采集、适配器、robots、登录态、Smoke Center、ML、数据 API 等。

常用验证：
```powershell
cd D:\智能数据分析平台\frontend
npm run build
```

```powershell
cd D:\智能数据分析平台\backend
.\venv\Scripts\python.exe -m pytest
```

针对性测试示例：
```powershell
cd D:\智能数据分析平台\backend
.\venv\Scripts\python.exe test_auth_integration.py
.\venv\Scripts\python.exe -m pytest test_smoke_contracts.py test_smoke_runner_non_auth.py test_smoke_assisted_auth.py
.\venv\Scripts\python.exe -m pytest test_capabilities_api.py test_data_api.py
```

OpenSpec 验证：
```powershell
cd D:\智能数据分析平台
openspec validate --all
```

注意：
- 当前环境若未安装 `requirements-v2.txt` 的所有依赖，后端全量 import / pytest 可能失败
- ML / DL / mining 依赖较重，排查主链问题时先关注 auth / crawl / analysis / data / reports / smoke
- Playwright、Scrapling、StealthyFetcher 相关测试可能依赖浏览器或额外运行时

## 14. 版本控制与本地文件边界

应该纳入版本控制：
- `backend/`、`frontend/`、`scripts/`、`docs/`
- `.codex/` 项目协作资产
- `AGENTS.md`
- `openspec/`
- Docker 定义，尤其 `docker-compose-v2.yml`
- 示例环境文件，例如 `backend/.env.example`

必须保持本地：
- `.env`、`backend/.env`
- Python 虚拟环境
- `node_modules/`
- `frontend/dist/`
- 本地数据库
- Cookie store / 登录态
- 训练模型产物：`.joblib`、`.pt`、`.pth`、`.onnx`
- 原始采集输出、处理后的运行数据
- 缓存、日志、临时文件、备份目录

当前工作区状态提醒：
- 该仓库当前存在大量未跟踪文件
- 修改前应先查看 `git status --short`
- 不要回滚或删除用户已有改动，除非用户明确要求

## 15. 工程偏好

通用原则：
- Python-first：后端、数据、ML、爬虫优先用 Python 现有结构
- 遵循现有模块边界，避免随手新增大而泛的抽象
- 能用 schema / parser / 结构化 API 时，不用脆弱字符串拼接
- 大变更先 OpenSpec，小修小补可直接实现但要保持范围清晰
- 对外部库、框架、CLI 的用法不确定时，用 Context7 查当前文档
- UI 改动后尽量用浏览器 / Playwright 做实际页面验证

后端偏好：
- 新 API 放在 `backend/api/routers/`
- 业务逻辑优先沉到对应 service / pipeline / crawler 模块，不要堆在路由函数里
- 新请求 / 响应结构优先使用 Pydantic schema
- 数据库访问使用已有 SQLAlchemy session 模式
- 采集能力优先扩展 adapter / crawler / intelligent strategy，不要复制一次性脚本逻辑进路由

前端偏好：
- 保持 `src/api/*` 与后端路由对应
- 页面组件放 `src/pages/`
- 可复用 UI 放 `src/components/`
- 状态放 `src/stores/`
- 组件库优先沿用 shadcn/ui、lucide-react、Tailwind 变量
- 前端展示应服务于数据分析工作流，避免只做装饰性视觉

验证偏好：
- 声称完成前必须跑相关验证
- 若无法运行测试，要说明原因和剩余风险
- 对爬虫、外部 API、登录态、人机协同流程，优先提供可复现的测试证据

## 16. 专家代理路由

项目本地 Codex 专家代理安装在 `.codex/agents/`。选择前先看：
- `.codex/memory/EXPERT_AGENT_QUICK_REFERENCE.md`
- `.codex/memory/EXPERT_AGENT_TRIGGER_PHRASES.md`

常用路由：
- 需求拆解 / 计划：`project-manager-senior`
- 后端 API / 服务边界：`engineering-backend-architect`
- 数据管线 / ETL / 入库：`engineering-data-engineer`
- ML / DL / 训练推理：`engineering-ai-engineer`
- 前端 / Dashboard / 可视化：`engineering-frontend-developer`
- 安全 / 登录态 / 权限 / 风险：`engineering-security-engineer`
- 代码审查：`engineering-code-reviewer`
- API 验证：`testing-api-tester`
- 事实核验 / 防止虚假通过：`testing-reality-checker`
- 测试证据收集：`testing-evidence-collector`
- 文档交接：`engineering-technical-writer`
- 多线协同：`agents-orchestrator`

除非用户明确要求并行代理，否则在当前 Codex 环境里优先在主线程顺序处理；只在工具调用层面并行读取文件或搜索。

## 17. 当前重点与风险

当前重点：
- 稳定 canonical 主链：auth / crawl / analysis / data / reports / smoke
- 让 Smoke Center 成为可复现验收入口
- 收敛 OpenSpec、文档和实际代码之间的差异
- 保持本地开发路径简单可靠

主要风险：
- 文档中存在旧状态，实际代码已有更新；写文档或做决策前要读当前文件
- 大量文件未跟踪，不能假定 git 历史完整反映项目状态
- Docker v2 引用了 `monitoring/` 配置路径，当前目录扫描未看到对应文件时要验证后再声称监控可直接运行
- `frontend/vite.config.ts` 和 `run-dev.ps1` 的前端端口不一致
- `ml/dl/mining` 依赖重，主 API 虽做了可选挂载，但完整功能验证依赖本地环境
- 登录态、Cookie、JustOneAPI Token、代理、验证码相关内容要按敏感数据处理

## 18. 小 c 接手提示

每次开始工作时：
1. 先读本文件和推荐阅读顺序中的核心文档
2. 用 `git status --short` 看工作区，保护用户改动
3. 找 canonical 入口，不要被 `*-v2` 或历史脚本带偏
4. 小任务直接改，大任务先 OpenSpec
5. 代码改动后跑最窄但有效的验证
6. 把重要新决策同步到 `.codex/memory/DECISIONS.md` 或相关文档

这个项目已经有不少可用零件，真正的工作重点不是再堆功能，而是把采集、入库、分析、报告、验收这些链路做稳、做清楚、做可复现。

## 19. 记忆系统快速规则

- 先读 `.codex/memory/MEMORY.md`，再决定是否下钻到长期记忆文件
- 新增重要运行事实时优先写 capture，再做 consolidate / sync
- 不要把 secrets、token、Cookie、登录态写进记忆文件
- 检索项目记忆时优先使用 Little C 本地索引，而不是人工翻很多文件
- 需要跨 session 或关系式检索时，再使用 `agentmemory`
- 如果 `agentmemory` 与 Markdown durable memory 出现冲突，以 Markdown durable memory 为准，并显式修正
- 如果 `understand-anything` 与 Markdown durable memory 出现冲突，以 Markdown durable memory 为准，并显式修正
- 如果科研技能给出的结论与项目数据/实验结果冲突，以项目数据和可复现实验为准，并显式修正
Use `.codex/memory/MEMORY.md` as the hot-start index before diving into the deeper durable memory files.
