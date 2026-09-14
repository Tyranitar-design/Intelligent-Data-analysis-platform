# 重建进度记录

> 每完成一个阶段在此追加：阶段号 / 完成项 / 验收命令 / 实测输出 / 遗留问题。
> 依据：`docs/REBUILD-SPEC-v3.md` 与 `docs/HERMES-PROMPT-v3.md`。

---

## 阶段 P0 · 收敛与基线治理

状态：**已完成 ✅**
开始：2026-09-14
完成：2026-09-14
提交：`c94620a`（73 files changed, +432 / -680）

---

### P0.0 基线快照 ✅

**问题**：仓库仅跟踪 9 个文件（全部属 auth-anticrawl day3），本地 575 个实际文件从未提交。
这是 GitHub 上项目看起来"残缺失败"的直接原因。

**动作**：`git add -A && git commit`，打 tag `v2-local-snapshot`。

**验收**：

```
$ git log --oneline -2
2b4fc30 chore(baseline): 建立重建前完整基线快照
af8406a feat(auth-anticrawl): Day 3 完成 - 登录态集成与测试

$ git status --short | wc -l
0

$ git count-objects -vH | grep size-pack
size-pack: 846.62 KiB
```

**结论**：回滚点建立，后续所有清理动作可安全执行。

---

### P0.1 环境验证 ✅

**动作**：验证后端与前端可运行性，确定基线。

**实测输出**：

```
$ ./venv/Scripts/python.exe -c "from api.main import app; print(len(app.routes))"
106

可选路由：
✅ Optional router available: api.routers.ml
✅ Optional router available: api.routers.dl
✅ Optional router available: api.routers.mining

端点：
200  /health
200  /capabilities
200  /api/v1/smoke/scenarios
200  /api/v1/smoke/contracts
200  /api/v1/crawl/adapters

$ npm run build
✓ 2005 modules transformed
✓ built in 1m
```

**遗留问题**：前端主 bundle **5,349 KB**（gzip 1,614 KB）严重超标。

根因：`antd` + `shadcn/ui` 双 UI 库并存；`plotly.js` + `echarts` + `recharts` 三图表库并存。

处理：P6 前端阶段解决（移除 antd、收敛图表库、路由级 code-split）。

**环境事实**（供后续命令参考）：

- Windows venv Python 可在 Linux 沙箱内经 `/mnt/d/.../venv/Scripts/python.exe` 直接调用（3.11.4）
- bash 工具需用 `workdir` 参数指定 Windows 路径，命令内 `cd D:/...` 会失败
- node/npm 位于 `D:\node.js`

---

### P0.2 数据库 schema 重建 ✅

**问题（阻断性）**：数据库按**旧模型定义**建立，代码库已 refactor 到 `api/models/` 包。
7 个 ORM 模型全部无法查询：

```
DataSource     no such column: data_sources.is_active
CrawlTask      no such column: crawl_tasks.name
Dataset        no such column: datasets.source_type
MLModel        no such column: ml_models.task_type
Report         no such column: reports.name
User           no such table:  users
AnalysisTask   no such table:  analysis_tasks
```

这是「后端能启动、106 个路由能注册、但任何真实数据库操作都崩溃」的根因。
表面健康、一用即废，是"失败品"印象的技术来源。

**证据**：旧库 `ml_models` 列为 `name, model_type, ..., training_time, status`；
新 ORM 期望 `algorithm, task_type, ..., training_time_seconds, cv_mean`。字段定义完全不同。

**动作**：新增 `backend/scripts/migrate_schema_v3.py`，流程为
备份 → 保留非 ORM 业务表 → 用当前 ORM 重建 → 回填 → 逐模型验证。

**实测输出**：

```
[1] backup created: data_platform.db.bak-20260914-040752
[2] preserved crawl_records: 54 rows, 9 cols
[2] preserved ecom_products: 852 rows, 18 cols
[2] preserved energy_data: 420 rows, 9 cols
[2] preserved news_data: 13 rows, 10 cols
[2] preserved stock_data: 120 rows, 13 cols
[3] old database removed
[4] new schema created from current ORM models
[5] restored crawl_records: 54 rows
[5] restored ecom_products: 852 rows
[5] restored energy_data: 420 rows
[5] restored news_data: 13 rows
[5] restored stock_data: 120 rows
[6] verification:
    OK   DataSource     rows=0
    OK   CrawlTask      rows=0
    OK   Dataset        rows=0
    OK   MLModel        rows=0
    OK   Report         rows=0
    OK   User           rows=0
    OK   AnalysisTask   rows=0

RESULT: all models queryable. Schema migration complete.
```

**验收**（迁移后端点，迁移前全部 500）：

```
200  /api/v1/reports/
200  /api/v1/data/tables/ecom_products/rows?limit=2   (6832 bytes)
200  /api/v1/data/tables/ecom_products/schema
200  /api/v1/data/tables/ecom_products/stats
200  /api/v1/data/overview
```

**回滚**：`mv data_platform.db.bak-20260914-040752 data_platform.db`

**数据保全**：5 张业务表、1459 行演示数据全部保留。

---

### P0.3 bcrypt 依赖修复 ✅

**问题（阻断性）**：`passlib 1.7.4` 与 `bcrypt 5.0.0` 不兼容。passlib 通过
`bcrypt.__about__` 探测版本，该属性在 bcrypt ≥ 4.1 已被移除，导致 passlib 走错代码
分支，密码哈希与校验抛 `ValueError: password cannot be longer than 72 bytes`。

后果：**注册与登录功能完全不可用**，`users` 表虽已建好却无法写入新用户。

**动作**：

- `api/routers/auth.py`：移除 passlib，直接调用 bcrypt，显式处理 72 字节截断
- `backend/requirements-v2.txt`：`passlib[bcrypt]==1.7.4` → `bcrypt==5.0.0`

**实测输出**：

```
REGISTER 200 → {"username":"smoke_probe","email":"...","id":1,"role":"analyst","is_active":true}
LOGIN    200 → {"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
ME       200 → {"username":"smoke_probe","email":"...","id":1,"role":"analyst"}
```

**意义**：项目历史上首次跑通完整认证链路（注册 → 登录 → 携带 token 访问受保护端点）。

---

### P0.4 消除同名模块/包冲突 ✅

**问题（阻断性）**：Python 导入歧义。同名模块与包并存：

| 同名对 | 状态 | 判定 |
|---|---|---|
| `api/models.py` / `api/models/` | 模块被包遮蔽 | 删模块 |
| `api/schemas.py` / `api/schemas/` | 模块被包遮蔽 | 删模块 |
| `api/database.py` / `api/core/database.py` | **两个都是活的** | 合并 |

第二组是真问题：两套独立的 engine、SessionLocal、Base 并存。`main.py` 只调用
`core.database.init_db()`，因此 `api/models.py` 里的模型**永远不会被建表**；
而 4 个 router 却用着旧栈的 `get_db`，且 `expire_on_commit` 行为不一致。

**动作**：

- 4 个 router + reports.py 的 `from api.database import get_db` 统一改为 `api.core.database`
- 删除 `api/database.py`、`api/models.py`、`api/schemas.py`
- 删除前确认：`PredictionTask` 仅被独立 Django admin 项目引用（与 FastAPI 无关）；
  `DataSourceBase` / `ErrorResponse` 无任何引用

**验收**：

```
残留引用扫描: clean
IMPORT OK, routes: 106
200  /health                    200  /api/v1/reports/
200  /capabilities              200  /api/v1/data/overview
200  /api/v1/crawl/adapters     200  /api/v1/analysis/db/data/datasets
```

---

### P0.5 删除重复入口 + 修复失效的 tailwind 配置 ✅

**动作一：删除 8 个重复入口**

```
backend/api/main-v2.py        backend/run_api.py
backend/run_api_simple.py     frontend/src/App-v2.tsx
frontend/package-v2.json      frontend/tailwind.config.cjs
frontend/postcss.config.cjs   docker-compose.yml
```

删除前验证：`main.tsx` 引用 `./App`；`run-dev.ps1` 使用 `uvicorn api.main:app`。

**动作二：修复失效的 tailwind 配置（发现一个真 bug）**

两个 tailwind 配置各有一半可用内容，而 Tailwind 的配置优先级是
`.js > .cjs > .mjs > .ts`，因此 `.cjs` **从未被加载**：

- `.js`（生效）：shadcn/ui CSS 变量色板、darkMode、container、accordion 动画
- `.cjs`（失效）：cyber 色板、fontFamily、marquee 动画、@tailwindcss/typography

后果：`components/cyber/*` 里使用的 `text-cyber-cyan`、`bg-bg-deep` 等类名
**从未被生成**，赛博主题实际处于失效状态。

处理：把 `.cjs` 独有内容合并进 `.js`，删除 `.cjs`。

**验收**：

```
$ npm run build
✓ 2005 modules transformed
✓ built in 38.47s
dist/assets/index-*.css   89.10 kB   (合并前 64.34 kB)

CSS 体积 +24.76 kB —— 证明此前未生成的 cyber 类名现已生效
```

---

### P0.6 测试归位 ✅

**问题**：`backend/` 根目录堆着 36 个 `test_*.py`。清点后发现：

- **25 个根本没有 test 函数**（一次性探索脚本）
- 11 个含 test 函数，其中仅 5 个真正含断言

**问题二**：`pytest --collect-only` 直接崩溃：

```
ValueError: I/O operation on closed file.
no tests collected, 1 error
```

根因：`test_alt_apis.py` 第 6 行在模块导入时执行
`sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)`，污染了 pytest 的 capture 机制。

**动作**：

- 5 个含断言的 → `tests/contract/`、`tests/integration/`
- 6 个有 test 函数但无断言 → `tests/legacy/`
- 25 个探索脚本 → `scripts/archive/`
- `check_*.py` / `populate_db.py` / `cleanup_db.py` / `crawl_jd_human.py` → `scripts/`
- 修复 `test_alt_apis.py`：改用 `sys.stdout.reconfigure()` 并加 `hasattr` 守卫
- 新增 `backend/pytest.ini`（`testpaths` / `pythonpath` / `norecursedirs`）

**验收**：

```
$ pytest --collect-only -q
tests/contract/test_smoke_contracts.py: 2
tests/integration/test_capabilities_api.py: 1
tests/integration/test_ml_pipeline.py: 4
tests/integration/test_smoke_assisted_auth.py: 3
tests/integration/test_smoke_runner_non_auth.py: 3
tests/legacy/*.py: 30

共 43 个测试，11 个文件，零错误
```

后端根目录已无任何 `test_*.py` / `check_*.py`。

---

### P0.7 文档收敛 ✅

根目录 6 份文档减至 3 份。归档（不删除，保留历史）到 `docs/archive/`：

```
README.md                      -> docs/archive/README-legacy.md
DESIGN.md                      -> docs/archive/DESIGN-legacy.md
DESIGN-v2-Enterprise.md        -> docs/archive/DESIGN-v2-enterprise.md
PROJECT_OPTIMIZATION_PLAN.md   -> docs/archive/PROJECT-OPTIMIZATION-PLAN.md
```

根目录保留：`AGENTS.md`、`AUTH-ANTICRAWL-GUIDE.md`、`README-v2.md`。

新增本文件与 `REBUILD-SPEC-v3.md`、`HERMES-PROMPT-v3.md`。

---

### P0.8 无关文件归档 ✅

`backend/alns_vrptw_{compare,destroy,repair,solver,state}.py` —— 五个 ALNS 车辆路径
求解器文件，与数据采集分析平台无关（疑似物流优化项目误入），移入 `scripts/archive/`。

---

## P0 完成总结

### 三个阻断性缺陷（本次修复的核心价值）

| # | 缺陷 | 症状 | 修复 |
|---|---|---|---|
| 1 | 数据库 schema 与 ORM 不同步 | 7 个模型全崩，106 路由里凡查库全挂 | 重建 + 回填，1459 行数据保留 |
| 2 | passlib 与 bcrypt 5.0 不兼容 | 注册/登录完全不可用 | 直接调用 bcrypt |
| 3 | 同名模块/包 + 双数据库栈 | 导入歧义 + 模型从未建表 | 统一到 core.database |

外加一个隐性缺陷：**tailwind 赛博色板从未生效**（配置优先级问题）。

### 项目状态变化

| 维度 | P0 前 | P0 后 |
|---|---|---|
| git 跟踪文件 | 9 | 430+ |
| 可信回滚点 | 无 | `v2-local-snapshot` + `c94620a` |
| 数据库 ORM 可用性 | 0/7 | 7/7 |
| 认证链路 | 不可用 | 注册→登录→鉴权 全通 |
| 根目录测试文件 | 36 个混杂 | 0 |
| pytest 收集 | 崩溃 | 43 个测试 |
| 重复入口 | 8 组 | 0 |
| 赛博主题 | 失效 | 生效 |
| 后端路由 | 106（部分坏） | 106（全可用） |

---

## 阶段 P1 · 判别内核

状态：**已完成 ✅**
完成：2026-09-14

目标：输入一个 URL，产出该站点的可采性画像与合规判定。这是「对任何网站适用」
从口号变成机制的关键一步。

### 交付内容

```
backend/discover/
  __init__.py     包入口与探测顺序说明
  fetcher.py      获取层：robots / sitemap / feeds / 主文档
  structure.py    结构识别：站点元信息、列表、分页、保护状态
  fields.py       字段发现：结构化数据提取 + 覆盖率合并
  profile.py      编排与持久化：SiteProfile 构建
backend/compliance/
  __init__.py
  engine.py       四维矩阵判定引擎
backend/api/models/site_profile.py          新增表 site_profiles
backend/api/models/compliance_verdict.py    新增表 compliance_verdicts
backend/api/schemas/discover.py             请求模型
backend/api/routers/discover.py             4 个端点
backend/tests/integration/test_discover_analyze.py   9 个测试
```

### 关键实现点

**探测顺序固定**（低成本高确定性优先）：

```
robots.txt → Sitemap/RSS 发现 → 主文档获取 → 保护状态判定
→ 结构化数据提取 → 列表/详情结构识别 → 分页识别
→ 详情样本抽样 → 字段覆盖率合并 → 四维判定 → 策略生成
```

这个顺序让多数站点在"结构化数据提取"一步就拿到干净数据，不需要进入渲染。

**robots.txt 按路径级判定**，不是整站开关。实现了 Allow 优先级、`*` 通配、
`$` 锚定的最长匹配语义。见到 `Disallow` 就放弃整站是判定错误。

**字段覆盖率为统计量**：同一字段在 N 个样本中命中 M 次 → 覆盖率 M/N。
详情样本会并入统计，让"这个字段值不值得采"有数据依据。

**判定引擎输出取证依据**：四维每一维都带理由字符串，判定可复核。

**SiteProfile 版本化**：结构无实质变化时原地更新避免版本膨胀，
有变化时新增 version 而非覆盖。

### 验证结果

**P1 测试**（`tests/integration/test_discover_analyze.py`）：

```
$ pytest tests/integration/test_discover_analyze.py -v
tests/.../test_normalize_url_pattern[5 cases]        PASSED
tests/.../test_robots_path_level_rules               PASSED
tests/.../test_full_analyze_flow                     PASSED
tests/.../test_second_analyze_hits_cache             PASSED
tests/.../test_captcha_page_is_blocked               PASSED

9 passed in 1.01s
```

**判定引擎七种场景实测**：

```
公开站点 + 官方通道      → proceed          A1/B1/C1/D1
需登录 + 未声明          → confirm_required A2/B4  + 4 条解锁条件 + token
验证码                   → blocked          A4     + 5 条替代源，覆盖率 0.989
第三方凭证               → blocked          B5     + 5 条替代源
自有凭证                 → proceed          A2/B2  + 凭证管理条件
个人数据                 → confirm_required A1/B4  （B4 优先级高于 D3）
书面授权 + 版权内容      → proceed          A1/B3/D2 + 用途限制条件
```

**结构识别实测**：站点类型分类（JSON-LD + 路径 + 文本三路证据）、
技术栈指纹（generator meta + 特征串）、列表模式（`li.news-item` × 4）、
分页（query param 'page'）、六种保护状态（captcha / cloudflare / paywall /
login_wall / http401 / none）全部正确。

**API 端点**：后端端点数 96 → 100。

```
POST /api/v1/discover/analyze              分析站点，产出画像 + 判定
GET  /api/v1/discover/profiles             列出已缓存画像
GET  /api/v1/discover/profiles/{id}        画像详情
GET  /api/v1/discover/verdicts             判定留痕（审计用）
```

### 未完成项（推迟）

`site_archetype` 站点原型库未实现。原型匹配需要累积一定数量的同域画像后
才有统计意义（规格里定的门槛是同域 ≥ 3 且结构相似）。留到 P2 之后，
有真实画像数据时再补。

---

## 阶段 P2 · 采集内核

状态：**已完成 ✅**（人机协同通道除外，见"未完成项"）
完成：2026-09-14

目标：把判别结果变成真正取回数据的能力——按评分选链、失败自动降级、
三级去重、自适应限速、可断点续跑。

### 交付内容

```
backend/collect/
  __init__.py
  registry.py           Capability 协议、注册表、评分选链
  ratelimit.py          按域名的自适应限速
  dedup.py              三级去重（主键 / SimHash / 语义接口）
  scheduler.py          任务编排、降级、入库、统计
  capabilities/
    _common.py              共享取页工具（限速 + 并发闸门 + robots 检查）
    feed_reader.py          RSS / Atom（最高优先）
    sitemap_walker.py       Sitemap 遍历
    structured_extractor.py 列表 → 详情 → 字段提取（主力）
    http_fetcher.py         单页兜底
    browser_renderer.py     公开页面渲染（运行时缺失时降级）
backend/api/models/collect_plan.py   新增表 collect_plans
backend/api/models/collect_job.py    新增表 collect_jobs / collect_tasks / collect_items
backend/api/schemas/collect.py
backend/api/routers/collect.py       6 个端点
backend/tests/integration/test_collect_pipeline.py  3 个端到端测试
```

### 关键实现点

**评分选链取代 if-else 分支**。每个能力实现 `score() / execute() / cost_estimate()`，
调度器按 `评分 × (1 + priority×0.1) × 画像推荐加权` 排序。实测五种画像的选链：

```
RSS 站点      → feed_reader → structured_extractor → http_fetcher → browser_renderer
Sitemap 站点  → sitemap_walker → structured_extractor → http_fetcher → browser_renderer
列表页静态    → structured_extractor → http_fetcher → browser_renderer
JS 渲染站     → browser_renderer → structured_extractor → http_fetcher
验证码站      → （空链，不执行）
```

**降级语义严格区分**：`DEGRADE` 表示本能力不适用、继续试下一候选；
`FAILED` 表示硬失败（如被目标拒绝），不再降级。

**自适应限速实测**：基准 10/s → 遇 429 降至 5/s → 连续 10 次成功后恢复至 6/s
→ 遇 503 降至 3/s 并遵守 `Retry-After 2s`。3 次请求在 3/s 节奏下耗时 2.69 秒。

**三级去重实测**：跟踪参数不变性（`?utm_source=x` 与无参数得到同一 item_key）；
近重复文本汉明距离 1，异文距离 32；同站点二次采集条目数不增长。

**合规强制点第二层防线**：`/collect/run` 在创建任务前查判定——
`blocked` 返回 403 + 替代源清单；`confirm_required` 要求携带有效令牌并校验有效期。

### 本轮修复的两个真 bug

**1. sitemap 解析器只看根的直接子节点**

标准结构是 `<urlset><url><loc>…</loc></url></urlset>`——`<loc>` 位于 `<url>` 之下，
原实现在根的子节点里找 `loc` 永远找不到，导致 sitemap 能力始终"未产出可用 URL"。
改为递归查找并兼容 `loc` 直接挂根的写法。

**2. 全部命中去重时错误降级**

增量采集时若所有条目都已采过，原实现返回 `DEGRADE`，调度器据此降级到兜底能力
（`http_fetcher`），把列表页本身也采成一条新数据——二次采集条目数从 3 涨到 4。
修复：全部命中属于"无新增"的正常结果，返回 `OK` 并记录 `known_hits`。

### 验证结果

```
$ pytest tests/integration/test_collect_pipeline.py tests/integration/test_discover_analyze.py -v
tests/integration/test_collect_pipeline.py ...        [ 25%]
tests/integration/test_discover_analyze.py .........  [100%]

12 passed in 9.61s
```

覆盖：完整采集闭环 / 二次采集增量去重 / sitemap 能力独立可用 /
URL 归一化 / robots 路径级判定 / 判别链路 / 缓存复用 / 验证码阻断。

端点数 100 → 106：

```
POST /api/v1/collect/plan        创建计划（不产生网络请求）
POST /api/v1/collect/run         执行计划（合规拦截点）
GET  /api/v1/collect/jobs        任务列表
GET  /api/v1/collect/jobs/{id}   任务详情（含分片状态与游标）
GET  /api/v1/collect/items       数据条目查询
GET  /api/v1/collect/registry    已注册能力清单
```

### 未完成项

1. **`collect/assist.py` 人机协同通道**未实现。需要在真实遇到验证码/登录墙时
   才有验证场景，留到有实际站点需求时补。
2. **断点续传只做了数据结构**（`CollectTask.cursor` 已落库），重入恢复逻辑
   尚未实现——当前每个 job 只有一个分片，续传语义还不构成瓶颈。

---

## 阶段 P3 · 数据管道

状态：**已完成 ✅**
完成：2026-09-14

目标：把采集条目变成可分析资产。

```
collect_items (原始 payload)
    → normalize   统一八种类型
    → pii         字段级最小化
    → storage     物化成真实表 + Dataset 记录
    → lineage     字段级血缘
```

### 交付内容

```
backend/pipeline/
  __init__.py
  normalize.py    类型推断、清洗、转换（八种统一类型）
  pii.py          PII 检测与最小化（哈希 / 打码 / 分箱 / 泛化 / 丢弃）
  lineage.py      字段级血缘构建与回溯
  storage.py      数据集物化、读取、清理
backend/api/models/audit_log.py   新增表 audit_logs
backend/api/models/dataset.py     扩展：user_id 改可空 + collect_job_id / profile_id
                                  / lineage / pii_policy / table_name
backend/api/routers/collect.py    新增 2 个端点
backend/tests/unit/test_pipeline.py                 57 个单元测试
backend/tests/integration/test_pipeline_materialize.py  4 个集成测试
```

### 关键实现点

**统一八种类型**：`text / int / float / bool / datetime / url / json / list`。
后续分析、检索、导出层只面对这八种，不必各自处理"价格是 ¥1,234.56 还是 1234.56"。

**PII 默认最小化**。默认动作是字段级处理而非整体弃采——真实数据集里个人数据
往往只占少数字段，因为一个作者名丢掉整包数据是不划算的。策略：

```
直接标识符（邮箱/手机/身份证/银行卡/姓名） → 哈希（保留可关联性且不可逆）
位置信息（地址）                          → 泛化到城市粒度
网络标识（IP）                            → 打码保留首尾
准标识符数值（年龄）                      → 区间分箱
```

检测先看格式（强证据）再看字段名（弱证据），不做过度推断——把一切当个人数据
会让平台失去可用性。

**物化成真实表**而非仅存 JSON，让分析层能直接 SQL 读取。表名 `ds_{dataset_id}`，
删除数据集时一并 DROP。中文列名用双引号保留，便于直接阅读查询结果。

**字段级血缘**：

```
dataset.field ← extractor_rule ← site_profile ← source_url
```

实测可追溯到 `json-ld:$.headline` 这一级的提取规则。

### 本轮修复的问题

| # | 问题 | 影响 |
|---|---|---|
| 1 | refactor 后的 `Dataset` 模型丢失 `table_name` 列 | 物化模块依赖该字段，直接 AttributeError |
| 2 | f-string 表达式内含反斜杠转义 | 语法错误，模块无法导入 |
| 3 | `drop_pii` 默认 False，PII 最小化从不执行 | 与"默认做字段级处理"原则矛盾，改为 `apply_pii=True` 默认开启 |
| 4 | 全角映射表只覆盖数字与符号，漏掉字母 | `１２３ＡＢＣ` 无法归一为 `123ABC` |
| 5 | 千分位逗号截断数字匹配 | `¥1,234.56` 被解析成 `1.0` |
| 6 | 测试清理顺序违反外键依赖，事务整体回滚 | "看似清理了其实一条没删"，残留数据让后续测试全部误判为已采集 |

第 6 项虽是测试代码问题，但暴露了一个通用陷阱：**SQLite 的外键约束会让整条事务
静默回滚**，表现为"操作没报错但数据没删"。删除多表数据时必须按依赖顺序从叶到根。

### 验证结果

```
$ pytest tests/unit/test_pipeline.py tests/integration/ -q
73 passed
```

单元测试 57 个（规范化 20 / PII 20 / 血缘 4 / 参数化展开），
集成测试 16 个（判别 9 / 采集 3 / 物化 4）。

物化链路实测：采集 3 条 → 规范化 → `author` 被识别为 PII 并哈希化 →
落成 `ds_N` 表 → 读取返回 3 行 → 血缘可追溯 → 删除数据集时物理表一并清理。

端点数 106 → 108：

```
POST /api/v1/collect/jobs/{job_id}/materialize   物化采集结果为数据集
GET  /api/v1/collect/datasets/{id}/preview       预览数据集内容
```

---

## 阶段 P4 · 分析层接入

状态：**已完成 ✅**
完成：2026-09-14

目标：让物化后的数据集直接进入分析链路，并把整条端到端打通。

### 交付内容

```
backend/analysis/facade.py       分析门面：以 dataset_id 为统一输入
backend/api/routers/analytics.py 4 个端点
backend/tests/integration/test_end_to_end.py  端到端验收（2 个测试）
```

### 关键实现点

**门面存在的理由**：现有 `AnalysisService` / `EDAEngine` 接收的是 DataFrame，
而平台的标准输入是数据集 ID。门面负责把"数据集"翻译成"DataFrame"，再把各引擎的
结果翻译成统一输出——**分析逻辑本身不重写**，只做适配。

**统一输出** `{dataset_id, analysis_type, result, charts, summary}`，
图表用 ECharts option 结构，前端可直接渲染。

支持六种分析：`eda` / `stats` / `correlation` / `outliers` / `missing` / `preview`。

**EDA 降级保护**：`EDAEngine` 导入失败时退回内置最小实现，保证分析链不中断。

**报告三格式**：markdown / html / json。报告含数据集概况、统计表、显著相关、
异常值、缺失情况、图表清单、**数据血缘**与**隐私处理记录**——后两项让报告本身
就能回答"数据从哪来、隐私怎么处理的"。

**导出三格式**：CSV（UTF-8 BOM，Excel 直接打开不乱码）/ JSON / Excel。

### 本轮修复的问题

| # | 问题 | 影响 |
|---|---|---|
| 1 | `verdict_uid` 由 `profile_id + hash(url)` 派生 | 重复判别同一 URL 必撞唯一约束，整条链在第二次运行时崩 |
| 2 | `Dataset` 模型缺 `dataset_type` 列 | `crawlers/dataset_service.py` 写入失败，`/smoke/run` 实际功能是坏的 |
| 3 | `dataset_service.py` 用旧列名 `columns_info` / `size_mb` | 同上，且它把 `source_type` 的值插进了 `dataset_type` 列（旧 bug） |
| 4 | 测试清理前未 rollback 悬挂事务 | 上个测试以 IntegrityError 结束时，清理静默失败，残留数据污染后续测试 |

第 1、2、3 项都是 **refactor 留下的新旧不一致**：模型改了但调用方没改，
而这些问题只在真正跑起来时才暴露——这正是"能启动但一用就崩"的那类缺陷。

### 验证结果

```
$ pytest tests/ -q
88 passed
```

**端到端验收测试**（`test_end_to_end.py`）覆盖七个环节：

```
1. 站点画像     domain / site_type=news / confidence>0.5 / has_sitemap
2. 合规判定     decision=proceed, A1
3. 采集执行     status=succeeded, items≥3, 每条数据均关联判定留痕
4. 物化数据集   row_count≥3, 物理表存在, 血缘非空, PII 策略非空
5. 分析         eda / stats（识别出数值字段）/ correlation / outliers
                图表含 ECharts option 与 series
6. 报告         markdown 含概况与血缘；html 含表格
7. 导出         csv / json / excel 三种格式均有内容且 media_type 正确
```

**幂等性测试**：二次执行整条链路，条目数不增长，去重统计显示命中增量。

端点数 108 → 112：

```
POST /api/v1/analytics/run                  执行分析
POST /api/v1/analytics/report               生成报告
GET  /api/v1/analytics/export/{dataset_id}  导出数据集
GET  /api/v1/analytics/types                支持的分析类型
```

### 测试配置调整

`tests/legacy/` 排除出默认收集。它们是 P0 归档的历史测试（依赖已变更的接口、
缺 pytest-asyncio 配置、多为无断言的连通性检查），记录的是上一代的验证方式，
不守护当前契约。文件保留供追溯。

### 端到端链路状态

```
输入 URL → 站点画像 → 合规判定 → 采集 → 入库 → 分析 → 报告导出
   ✅        ✅         ✅       ✅     ✅     ✅      ✅
```

七个环节全部打通，并有自动化测试守护。

---

## 阶段 P5 · MCP 工具面

状态：**已完成 ✅**
完成：2026-09-14

目标：把平台能力以 MCP 工具形式暴露，供 Hermes 等 24 小时在线的代理调用。

### 交付内容

```
backend/mcp/
  __init__.py
  protocol.py    JSON-RPC 2.0 消息类型与错误码
  registry.py    工具注册表与入参校验
  auth.py        Bearer 鉴权（fail-closed）
  audit.py       审计写入（入参只存摘要哈希）
  server.py      协议处理器
  tools/
    __init__.py     七个工具聚合
    discovery.py    analyze_site / plan_collection / run_collection / job_status
    analytics.py    query_dataset / run_analysis / make_report
backend/api/routers/mcp.py   HTTP 端点
backend/collect/planner.py   计划构建与合规校验（从路由抽出，REST 与 MCP 共用）
backend/tests/integration/test_mcp_server.py  17 个测试
```

### 关键设计

**自实现协议而非引入 SDK**。MCP 的传输核心很薄（`initialize` / `tools/list` /
`tools/call`），自实现是零新依赖，同时减少 Lite 形态（Hermes 服务器）的部署负担
与版本兼容风险。包名与官方 SDK 同名这点已在 `mcp/__init__.py` 注明——
当前环境未安装 SDK，将来引入需先做命名隔离。

**fail-closed 鉴权**。未配置 `MCP_API_KEY` 时拒绝所有需鉴权的调用，
而不是静默放行。配置缺失属于部署错误，不该表现为"谁都能调"。
token 用 `secrets.compare_digest` 常量时间比较，避免时序侧信道。

**敏感入参不入审计**。入参先对 `authorization_token` / `password` / `api_key`
等键做脱敏，再计算摘要哈希；审计表里只有哈希值，没有原文。

**工具粒度固定为七**。更细会让调用方承担编排责任、错误率上升；
更粗会让调用方失去控制点和中间反馈。这七个覆盖
「分析 → 规划 → 执行 → 观察 → 取数 → 分析 → 交付」全环。

**计划构建逻辑抽出到 `collect/planner.py`**，REST 端点与 MCP 工具共用同一实现——
两个入口本该只有一套逻辑，这是 P0 定下的单一定义原则的延续。

### 本轮修复的问题

**鉴权失败未写审计**。`authenticate()` 在审计写入之前抛出，导致被拒绝的调用
不留痕——而安全审计的重点恰恰是失败尝试。已修复：鉴权失败同样记
`result="denied"` 并附 `stage="auth"`。

**入参类型校验漏掉 bool**。Python 里 `bool` 是 `int` 的子类，
`{"dataset_id": True}` 会被当成 `1` 通过校验。已在类型校验中显式排除。

### 验证结果

```
$ pytest tests/integration/test_mcp_server.py -q
17 passed
```

覆盖：协议方法（initialize / ping / tools/list / 未知方法 / 非法 JSON / 通知）、
鉴权（未配置 / 缺头 / 错 token / 正确 token / 多 token 多身份）、
参数校验（未知工具 / 缺必填 / 类型错误 / bool 混入）、审计留痕与敏感值不落库。

协议实测：

```
GET  /mcp                      → 200，7 个工具，auth_configured 状态
POST initialize                → protocolVersion 2024-11-05
POST tools/list                → 7 tools（每个含 inputSchema）
POST ping                      → {}
POST 未知方法                   → -32601
POST tools/call（未鉴权）      → -32001 AUTH_REQUIRED
POST tools/call（错 token）    → -32002 INVALID_TOKEN
```

### 接入方式

```bash
# 1. 配置 token（.env）
python -c "import secrets;print(secrets.token_urlsafe(32))"
# 写入 MCP_API_KEY=<token>:hermes

# 2. 启动服务
run-dev.cmd start

# 3. 验证
curl http://127.0.0.1:8000/mcp
```

Hermes 侧配置 MCP 端点 `http://<host>:8000/mcp`（streamable-http），
带 `Authorization: Bearer <token>`。

### 未完成项

- 部署脚本（systemd / Windows 服务 / Docker）未提供，当前用 `run-dev.cmd` 手动启动
- 两形态协作（本机 ↔ Hermes）未打通，设计上留到 P7

---

## 阶段 P6 · 企业级前端

状态：**进行中**（核心重构已完成，待视觉打磨与运行验证）
开始：2026-09-14

### 已交付

```
frontend/src/index.css                     设计系统（替换 shadcn 变量 + 组件类 + 动效）
frontend/src/components/layout/MainLayout.tsx  侧边栏 + 顶栏 + 内容区
frontend/src/pages/
  Dashboard.tsx    工作台（概览指标 + 最近任务 + 快捷入口）
  Discover.tsx     站点分析（核心页：URL 输入 → 画像 + 判定 + 字段 + 策略）
  Collect.tsx      采集任务（三层视图 + 一键物化）
  Datasets.tsx     数据集（列表 + 数据预览）
  Analytics.tsx    数据分析（类型选择 + ECharts 渲染 + 结果表）
  Reports.tsx      报告（生成 + 预览 + 复制 + 导出）
frontend/src/lib/echarts.ts                ECharts 按需注册
```

### 体积治理（成果显著）

| 阶段 | 主包 | gzip |
|---|---|---|
| 治理前 | 5,349 KB | 1,614 KB |
| 移除 antd / plotly / recharts | 1,527 KB | 501 KB |
| ECharts 改按需注册 | 1,068 KB | 352 KB |
| 配置 manualChunks 分包 | 见下 | — |

最终产物：

```
index.html              0.80 kB  (gzip   0.52 kB)
index.css              96.07 kB  (gzip  15.57 kB)
motion-vendor          96.16 kB  (gzip  31.76 kB)
react-vendor          164.04 kB  (gzip  53.54 kB)
index（业务代码）      230.07 kB  (gzip  72.48 kB)
chart-vendor          578.12 kB  (gzip 194.28 kB)
```

**首屏只需 587 KB（gzip 174 KB）**，比治理前降低约 89%。
图表库独立成块，只在访问分析页时加载，且其哈希不随业务代码变更、可长期缓存。

治理的关键发现：**antd 与 plotly 各自只被 1 个文件引用，却带来约 4.5 MB**。
先摸清真实引用面再动手，比按体积猜测有效得多。

### 设计系统

替换 shadcn/ui 的 CSS 变量即可让 40+ 个组件整体换装——这是成本最低、
一致性最高的换肤方式。视觉方向：深空底色（222 系深灰，非纯黑）+ 青蓝主色（186）
+ 琥珀强调（38）。

提供的基础设施：`.glass` 玻璃面板、`.glass-hover` 悬停透光、`.grid-bg` 网格底纹、
`.aurora` 顶部光晕、`.mono-tag` 等宽数据标签、`.badge-*` 状态徽标、
`.animate-rise` 入场、`.animate-scan` 扫描线、`.animate-pulse-soft` 呼吸。
并遵守 `prefers-reduced-motion`。

### 本轮修复的问题

| # | 问题 | 影响 |
|---|---|---|
| 1 | `themeStore` 只设 `data-theme` 属性，而 Tailwind 用 `dark:` class 变体 | 深色变量与 `dark:` 样式全部不生效 |
| 2 | `vite.config.ts` dev 端口写 3000，启动脚本用 5173 | 端口不一致，排查困难 |
| 3 | 代理只配了 `/api`，未含 `/capabilities` | 首页请求能力状态会打到 Vite 自己身上并 404 |
| 4 | `components/MainLayout.tsx`（452 行 antd 版）无引用仍存在于源码 | 它是 antd 的唯一使用者，不清掉就无法移除依赖 |

### 运行验证（已完成）

新增 `backend/scripts/verify_stack.py`：启动前后端 → 轮询等待就绪 → 验证端点
→ 验证代理 → 清理。

实测结果：

```
[1] starting backend (:8000) ...
  backend ready
[2] backend endpoints
  OK      200  /health
  OK      200  /capabilities
  OK      200  /api/v1/data/overview
  OK      200  /api/v1/collect/jobs
  OK      200  /api/v1/collect/registry
  OK      200  /api/v1/analytics/types
  OK      200  /api/v1/discover/profiles
  OK      200  /mcp
[3] starting frontend (:5174) ...
  frontend ready
[4] frontend page and proxy
  OK      200  / (index page)
  OK      200  /capabilities (via proxy)
  OK      200  /api/v1/data/overview (via proxy)
  OK      200  /api/v1/analytics/types (via proxy)
RESULT: all checks passed
```

排查过程中发现并修复的三个环境问题：

1. **轮询替代固定 sleep**。后端冷启动需 15~25 秒（依赖多），固定 sleep 要么浪费
   时间要么不够——这是最初几次验证"看起来后端没起来"的真实原因。
2. **Vite 默认只监听 IPv6**：`[::1]:5174` 通而 `127.0.0.1:5174` 不通。给 vite 传
   `--host 127.0.0.1` 可解。浏览器访问 localhost 不受影响（双栈尝试），
   但脚本与 curl 探测会踩坑。
3. **npm 派生 vite 需要杀进程树**：只 terminate npm 会留下孤儿 vite 继续占端口，
   下次启动报 "Port already in use"。Windows 下改用 `taskkill /F /T`。
4. **脚本输出必须用 ASCII 标记**：Windows 控制台默认 GBK，勾叉类符号会触发
   `UnicodeEncodeError` 直接中断脚本。

### 视觉与适配（已完成）

**粒子背景层**（`components/visual/ParticleField.tsx`）：全屏 Canvas 粒子网络。
设计取向「能感觉到但不抢戏」——密度上限 72、只连近邻、指针产生斥力而非吸引。
按 devicePixelRatio 适配（封顶 2 倍）；标签页不可见时暂停；尊重
`prefers-reduced-motion`（此时完全不渲染）。

**骨架屏**（`components/visual/Skeleton.tsx`）：六个变体（文本 / 指标卡 / 卡片 /
表格 / 图表 / 基础块），已接入数据集列表与分析执行。用骨架而非 spinner 的
理由：骨架预示内容结构与规模，避免加载完成后的布局跳动。

**响应式**：小屏（< lg）侧边栏改为抽屉 —— 含路由切换自动收起、打开时锁定
页面滚动、遮罩点击关闭。三个数据表格加横向滚动与最小宽度，避免窄屏挤断。

### 待办（可选增强）

- [ ] 空态插画：当前空态为纯文字，可加入轻量示意图形
- [ ] `tsconfig` 排除 `_legacy` 目录，为将来的 `tsc` 类型检查铺路
- [ ] 截图回归：本环境浏览器需手动启动调试端口，未接入自动截图；
      本地可用 `cdp_shot` 工具补
- [ ] 响应式实测：抽屉与横滚在真实窄屏设备上的表现待人工确认

### 归档说明

旧页面（17 个）与旧设计资产移入 `src/pages/_legacy/` 与 `src/components/_legacy/`，
保留但不参与构建。其中 `components/cyber/*` 八个赛博视图与 `ParticleNetwork.tsx`
是后续视觉打磨的素材来源——移除依赖时才需要处理它们在 `_legacy` 里的 recharts 引用。

---

## 待确认（需 YG 决策）

1. 测试用户 `smoke_probe`（id=1）为 P0.3 验收产生，保留还是清理？
2. 前端历史组件 `components/cyber/*`（8 个赛博视图）与 `pages/CyberIndex.tsx` 如何处置：
   作为 P6 新前端的设计基础保留，还是推倒重做？
3. P6 前端体积治理方案确认：移除 `antd`（与 shadcn/ui 重复）、图表库收敛为 ECharts 单一
   （现为 plotly + echarts + recharts 三套并存），预计可把 5.35 MB 主包降至 1.5 MB 以内。

---

## 阶段 D1 · 测试库隔离 + 主库脏表清理

状态：**已完成 ✔**
开始：2026-09-14
完成：2026-09-14
依据：`docs/UPGRADE-PLAN-v4.md` §1.2 问题 1 + `docs/UPGRADE-PLAN-v5.md` §4.3

### 背景（先复现，再修复）

主库 `backend/data_platform.db` 中堆积 `dataset_smoke_*` 表 —— smoke 契约测试
每次运行都在主库物化数据集，只增不减。

实测复现（跑一次全量测试）：

```
跑前：41 张表 / 21 张 smoke 表 / datasets 10 行
跑后：43 张表 / 23 张 smoke 表 / datasets 12 行   ← 每跑一次 +2 表 +2 记录
```

根因是**两条数据库腿**各自为政：

| 腿 | 实现 | 配置源 |
|---|---|---|
| SQLAlchemy | `api/core/database.py` | `settings.DATABASE_URL`（读 env / .env） |
| sqlite3 | `database/models.py` | **硬编码** `backend/data_platform.db` |

且第二条腿被 `crawlers/dataset_service.py`（smoke 保存数据集）与
`api/routers/data.py`（数据浏览）使用 —— 测试跑 smoke 链路时必然写主库。

### 修复（4 件）

1. **`database/models.py`**：`Database` 默认路径改走统一配置源，新增
   `resolve_default_db_path()`（env `DATABASE_URL` > `backend/.env` > 历史默认）
   与 `_parse_sqlite_path()`。两条数据库腿自此由同一份配置驱动。
2. **`tests/conftest.py`**（新增）：在任何后端 import 之前把 `DATABASE_URL`
   指向会话级临时库（`%TEMP%/webinsight_pytest/test_data_platform.db`），
   session 级 fixture 建表；每次会话全新开始，互不串味。
3. **`scripts/clean_smoke_tables.py`**（新增）：主库清理工具，预演 / `--apply`
   两模式、自动备份、幂等。
4. **`tests/unit/test_db_isolation.py`**（新增）：两条哨兵 ——
   ① 测试运行时两条腿都指向隔离库；② 主库不允许出现 `dataset_smoke_*` 表。

### 验收命令与实测输出

```
$ .\venv\Scripts\python.exe scripts\clean_smoke_tables.py --apply
已备份主库: data_platform.db.bak-20260914-112432
清理完成: 剩余 smoke 表 0，主库现有 20 张表。

$ .\venv\Scripts\python.exe -m pytest
107 passed, 21 warnings in 42.11s        ← 105 原有 + 2 哨兵，全绿

# 隔离验证（跑完全量测试后的对照）
主库   : 20 张表（不变）· smoke 表 0 · datasets 0 行
测试库 : %TEMP%\webinsight_pytest\test_data_platform.db
         22 张表 · smoke 表 2（新产生的两份全部落在隔离库内）
```

### 遗留

- pytest 警告（Pydantic v2 / SQLAlchemy 2.0 deprecation）为存量问题，另行清理。
- P6「待确认」三条仍待 YG 拍板。
- 下一步：F1 动效基础设施（v5 蓝图 P11a）。

---

## 阶段 F1 · 动效基础设施（v5 蓝图 P11a）

状态：**已完成 ✔**
开始：2026-09-14
完成：2026-09-14
依据：`docs/UPGRADE-PLAN-v5.md` §2.2（动效四层分级）、§4.2（P11a）

### 交付（L0/L1 基础设施 + 最小接入）

| 件 | 位置 | 说明 |
|---|---|---|
| 滚动揭示 | `components/motion/Reveal.tsx` | position-driven（whileInView）、once、错峰延迟、reduced-motion 直落 |
| 数字滚动 | `components/motion/CountUp.tsx` | rAF + easeOutCubic，零依赖；更新时从当前值滚到新值 |
| 卡片微倾斜 | `components/motion/Tilt.tsx` | ±2.5° 鼠标跟随；reduced-motion 不启用 |
| 页面转场 | `components/layout/MainLayout.tsx` | AnimatePresence + useOutlet，180ms；reduced-motion 时禁用 |
| 图表编排 | `lib/echarts.ts` | `CHART_MOTION`（800ms cubicOut）；后端显式 option 优先 |
| reduced-motion 补强 | `index.css` | 补 `scroll-behavior: auto` 覆盖 |

接入点：工作台（4 张统计卡 CountUp + Tilt、两个区块 Reveal）、数据分析（图表动效）、全局（页面转场）。

### 验收（实机门禁，证据落盘 `docs/evidence/f1-verify/`）

```
$ .\venv\Scripts\python.exe scripts\verify_frontend_f1.py
OK    frontend ready / backend ready
OK    brand visible / stat cards rendered (>=4)
OK    countup shows number  --  19
OK    transition has in-between frames
      samples=['1','0.500352','0.286616','0','0.25953','0.72312','0.985072','0.999999']
OK    discover page rendered / route back to dashboard
OK    reduced-motion renders + final values
OK    no console errors (normal mode / reduced-motion)
RESULT: all checks passed
```

转场采样序列（旧页 1→0 → 新页 0→1 的完整中间帧）是「动画在真实路径
上被触发」的直接证据——复刻纪律「形状完整 ≠ 在跑」的正面应用。

### 附带验证

- `npx tsc --noEmit`：本次涉及文件零错误；存量 24 个错误全部在 `_legacy`
  与未使用 UI 组件（react-day-picker / embla 等未安装依赖），留待 P6 待办清理。
- `npm run build` 绿（26.8s）；vendor 分包（react/motion/chart）后首屏
  JS+CSS ≈ 176KB gzip，低于 v5 蓝图 300KB 预算。

### 遗留

- 存量 tsc 错误清理（与 `_legacy` 归档策略一并处理）。
- L2/L3 动效（采集管道可视化、合规矩阵、展示岛）按 v5 蓝图 P11a 后续 / P12 推进。

---

## 阶段 E2 · 定时调度（v5 蓝图 P7 核心项）

状态：**已完成 ✔**
开始：2026-09-14
完成：2026-09-14
依据：`docs/UPGRADE-PLAN-v5.md` §4.3（如果只做三件事 · 第三件）

### 交付

| 件 | 位置 | 说明 |
|---|---|---|
| 调度模型 | `api/models/schedule.py` | 结构化频率（hourly / daily / weekly），本机时间口径 |
| 调度运行器 | `collect/schedule_runner.py` | next_run 计算（零依赖）+ 到期触发 + 常驻循环 + 合规门 |
| API | `api/routers/collect.py` | plans 列表 + schedules CRUD + 立即执行（共 6 个新端点） |
| 前端 | `frontend/src/pages/Schedules.tsx` | 调度中心：可视化频率选择、启停、立即执行、累计统计 |
| 测试 | `tests/unit/test_schedule_next_run.py` + `tests/integration/test_schedules_api.py` | 24 个（频率计算 15 + API/合规 9） |

### 合规加固（两处，均在实机验证中暴露后修复）

1. **调度路径合规门**：无人值守路径只放行 `proceed` 计划——创建调度时拦截（400），
   执行时兜底（`skipped_compliance` + 顺延 next_run 防死循环）。与 `/run` 端点同源检查。
2. **`discover/profile.py` 缓存路径判定留痕缺陷**（既有 bug，被合规门暴露）：
   画像命中缓存时本次判定不落库、`verdict_id` 引用旧记录——`declared_authorization`
   变化时调用方拿到与结论不符的 uid。修复：缓存路径同样 `_record_verdict`。

### 验收（实机门禁 13/13，证据 `docs/evidence/e2-verify/`）

```
$ python scripts/verify_schedules_e2.py
OK  plan A confirm_required (no declaration)          <- 反例：未声明授权
OK  compliance gate rejects confirm_required plan     <- 合规门拦截
OK  plan B proceed (declared official)                <- 正例：声明官方开放
OK  schedule created with next_run / pause / resume
OK  schedule loop auto-triggered  --  run_count=1 last_job=1
OK  auto-triggered job recorded   --  job=1 status=succeeded items=1
OK  manual run executed           --  job=2 status=succeeded run_count=2
OK  frontend schedules page renders list
OK  cleanup test data
RESULT: all checks passed
```

### 遗留

- 调度循环周期由 `SCHEDULE_TICK_SECONDS` 控制（默认 15s；仅长驻进程启用，测试不触发）。
- P7 剩余项：E3 断点续传重入恢复、`/sites` 站点库、`/collect/:jobId` 任务详情。
- `_latest_verdict` 成为 dead code（保留待用）。

---

## 阶段 P8a · 合规中心（v5 蓝图 Wow S3 载体）

状态：**已完成 ✔**
开始：2026-09-14
完成：2026-09-14
依据：`docs/UPGRADE-PLAN-v4.md` §4.5（C1）+ `docs/UPGRADE-PLAN-v5.md` §2.3（Wow 时刻）

### 交付

| 件 | 位置 | 说明 |
|---|---|---|
| 统计端点 | `GET /discover/verdicts/stats` | 决策分布 + A×B 矩阵聚合 |
| 补齐授权 | `PATCH /discover/verdicts/{uid}/authorization` | 写回 operator / basis + 解锁为 proceed + 审计留痕（复用 `mcp.audit.record`） |
| 前端页面 | `frontend/src/pages/Compliance.tsx` | 统计卡 + A×B 热力矩阵 + 待确认（补齐表单）+ 已阻断（替代源与覆盖率）+ 全部判定（展开四维取证） |
| 导航 | 侧边栏新增「平台治理」分组 | 合规中心入口 |
| 测试 | `tests/integration/test_compliance_api.py` | 6 个：stats delta / 解锁+审计 / blocked 拒绝 / proceed 拒绝 / 404 / 枚举校验 |

### 设计要点

- 阻断判定**不提供解锁**——硬边界（技术措施 / 凭证来源 / 数据属性）不因人工确认而改变；
- 补齐授权是"写回判定 + 审计留痕"的组合动作，审计写入 `audit_logs`
  （action=`compliance.authorization_confirmed`，外键关联判定记录）；
- 矩阵用数据驱动着色（没有装饰性颜色），符合"合规判定不加粉饰"的原则。

### 验收（实机门禁 9/9，证据 `docs/evidence/p8-compliance/`）

```
$ python scripts/verify_compliance_p8.py
OK  seed verdicts created  --  confirm_required=2 proceed=1
    example.com -> confirm_required / www.iana.org -> confirm_required / docs.python.org -> proceed
OK  stats total grows by seeds  --  3 -> 6
OK  stats by_decision populated  --  {'proceed': 2, 'confirm_required': 4, 'blocked': 0}
OK  stats matrix non-empty  --  2 cells
OK  authorization confirmed and unlocked  --  decision=proceed operator=yg-verify
OK  compliance page renders
RESULT: all checks passed
```

种子数据（保留为平台资产）：example.com、www.iana.org（待确认，其中一条已补齐解锁）、
docs.python.org（可执行）。

### 遗留

- P8 剩余项：审计检索页（`/audit`）、运行监视（`/monitor`）、接入管理（`/integrations`）。
- 种子判定与审计日志保留（审计不提供逐条删除，清理走保留策略）。

---

## 阶段 P8b + F2 · 页面三连（审计检索 / 任务详情 / 工作台 Hero）

状态：**已完成 ✔**
开始：2026-09-14
完成：2026-09-14
依据：`UPGRADE-PLAN-v4.md` §4.9（审计）+ §4.7（任务详情）+ `UPGRADE-PLAN-v5.md` §2.3（工作台 Hero）

### 交付

| 件 | 位置 | 说明 |
|---|---|---|
| 审计端点 | `GET /api/v1/audit/logs` | 过滤（action 前缀 / principal / result / verdict）+ 分页；**不提供删除** |
| 审计字段 | `AuditLog.to_dict()` | 补 `request_digest` 透传 |
| 审计页 | `frontend/src/pages/Audit.tsx` | 筛选组 + 留痕表 + 行展开详情（digest / 判定关联 / detail） |
| 任务详情页 | `frontend/src/pages/JobDetail.tsx` | 数据驱动管道（判别→采集→去重→入库）+ 时间线 + 降级链 + 动态列条目表 + 物化按钮 |
| 工作台 Hero | `Dashboard.tsx` | 定位语「任意站点，从可采判定到洞察报告」+ 双 CTA |
| 入口/路由 | Collect 列表详情箭头；`/audit`、`/collect/:jobId` 路由；导航「审计日志」 | |

### 验收（实机门禁 11/11，证据 `docs/evidence/p8b-f2/`）

```
$ python scripts/verify_pages_p8b.py
OK  plan created (proceed)  --  plan_id=1 decision=proceed
OK  collect run completed  --  job=1 status=succeeded items=1
OK  materialized to dataset  --  dataset=1 rows=1 cols=1
OK  fresh confirm_required verdict  --  decision=confirm_required
OK  unlocked with audit trail  --  operator=verify-p8b
OK  audit log shows unlock action  --  total=2
OK  dashboard hero renders  --  slogan found
OK  job detail renders (pipeline + items)  --  job=1
OK  audit page renders with unlock action
RESULT: all checks passed
```

截图：`01-dashboard-hero.png` / `02-job-detail.png` / `03-audit.png`。

### 遗留

- 审计覆盖面：当前仅合规解锁与 MCP 工具调用写审计；采集执行 / 数据集物化 /
  导出 的审计点仍待补（v4 §4.9 所列动作清单）。
- P8 剩余项：运行监视（`/monitor`）、接入管理（`/integrations`）。

---

## 阶段 P8c · 数据集详情（v4 第一档收官）

状态：**已完成 ✔**
开始：2026-09-14
完成：2026-09-14
依据：`UPGRADE-PLAN-v4.md` §4.4（数据集详情 / 第一档）

### 交付

| 件 | 位置 | 说明 |
|---|---|---|
| 元信息增强 | `pipeline/storage.py::read_dataset` | 返回体带 `dataset`（schema / lineage / pii_policy / statistics），向后兼容 |
| 详情页 | `frontend/src/pages/DatasetDetail.tsx` | 字段概览（类型/覆盖/PII/范围）+ 字段级血缘 + 分页预览 + CSV/JSON/Excel 导出 |
| 入口 | Datasets 卡片底部「详情」链接 | |
| 血缘修复 | `pipeline/lineage.py::_extract_rule_map` | 避免 `css:css:h1` 双重前缀（path 自带 source 前缀时去重） |
| 验证 | `scripts/verify_dataset_detail_p8c.py` | 元信息 + 双格式导出 + 页面渲染 |

### 验收（实机门禁 8/8，证据 `docs/evidence/p8c-dataset/`）

```
$ python scripts/verify_dataset_detail_p8c.py
OK  backend/frontend ready
OK  preview carries dataset meta  --  dataset=1 name=collect_job_1_20260914-040910
OK  meta has schema/lineage/pii fields  --  schema=yes lineage=yes
OK  preview rows readable  --  rows=1 / total=1
OK  csv export works  --  bytes=61 type=text/csv
OK  json export works  --  bytes=96
OK  dataset detail renders (fields + lineage + preview)
RESULT: all checks passed
```

### v4 第一档进度

站点库 / 数据集详情 / 合规中心 / 接入管理 —— **数据集详情 + 合规中心已完成**；
站点库（`/sites`）与接入管理（`/integrations`）待做。

### 遗留

- 站点库 `/sites`（画像资产化，P7 剩余）
- 运行监视 `/monitor`、接入管理 `/integrations`（P8 剩余）

---

## 阶段 P7a · 站点库（v4 第一档收官）

状态：**已完成 ✔**
开始：2026-09-14
完成：2026-09-14
依据：`UPGRADE-PLAN-v4.md` §4.3（站点库 / 第一档）

### 交付

| 件 | 位置 | 说明 |
|---|---|---|
| 统计端点 | `GET /discover/profiles/stats` | 判定/类型分布 + 过期计数（>14 天）；路由注册在 `{profile_id}` **之前**（测试守护防遮蔽） |
| 列表增强 | `list_profiles` | 补 `field_count` |
| 站点库页 | `frontend/src/pages/Sites.tsx` | 统计条 + 判定筛选 + 域名搜索 + 卡片网格（置信/覆盖/字段/时效/过期角标）+ 详情抽屉（访问状态/结构/字段表/策略/判定/时间线）+ **重新探测**（复用 analyze force_refresh=true） |
| 入口 | 侧边栏「采集链路」新增「站点库」 | |
| 测试 | `tests/integration/test_profiles_stats.py` | 2 个（delta 聚合 + 路由遮蔽守护） |
| 验证 | `scripts/verify_sites_p7a.py` | 8 项断言 + 双截图 |

### 验收（实机门禁 8/8，证据 `docs/evidence/p7a-sites/`）

```
OK  profiles available  --  count=3 first=docs.python.org
OK  list carries field_count  --  field_count=2
OK  stats total matches  --  total=3
OK  stats by_decision populated  --  {'proceed': 1, 'confirm_required': 2, 'blocked': 0}
OK  sites page renders (stats + cards) / profile drawer renders (access + fields)
RESULT: all checks passed
```

实况：docs.python.org（可采）/ www.iana.org / example.com（待确认）三张真实画像。

### v4 第一档收官

| 页面 | 状态 |
|---|---|
| 站点库 `/sites` | ✅（本阶段） |
| 数据集详情 `/datasets/:id` | ✅（P8c） |
| 合规中心 `/compliance` | ✅（P8a） |
| 接入管理 `/integrations` | ⏳ 待做 |

### 遗留

- 探测层 `fields[].path` 存在 source 前缀重复（如 `css:css:[role='main']`），
  展示层不再拼接，待探测层统一清洗。
- 批量操作（多选重探测 / 导出画像）未做（v4 可选互动）。
- 接入管理 `/integrations`、运行监视 `/monitor`（P8 剩余）。

---

## 阶段 P8d · 运行监视（含共享限速器修复）

状态：**已完成 ✔**
开始：2026-09-14
完成：2026-09-14
依据：`UPGRADE-PLAN-v4.md` §4.10（运行监视）

### 交付

| 件 | 位置 | 说明 |
|---|---|---|
| **共享限速器**（关键修复） | `collect/ratelimit.py` + `collect/scheduler.py` | `get_shared_limiter()` 进程级单例——此前每个调度器实例新建限速器，"自适应"只在一个请求内生效；现在被 429 降速/恢复进度跨请求存续 |
| 监视端点 | `GET /api/v1/monitor/stats` | service / queue / rate / storage 四段聚合 |
| 监视页 | `frontend/src/pages/Monitor.tsx` | 四卡 + 域名限速表（基准→当前/请求数/被限速/连续成功/状态）+ 存储明细 + 自动刷新开关（30s） |
| 入口 | 侧边栏「平台治理」新增「运行监视」 | |
| 测试 | `tests/integration/test_monitor_api.py` | 3 个（契约 / 队列 delta / 限速表追踪） |
| 验证 | `scripts/verify_monitor_p8d.py` | 6 项断言 + 截图 |

### 验收（实机门禁 6/6，证据 `docs/evidence/p8d-monitor/`）

```
OK  stats four sections contract  --  version=2.0.0 tables=22 db_bytes=598016
OK  collection executed  --  job=2 status=succeeded
OK  rate table tracks collected domain  --  domains=['example.com']
OK  monitor page renders (cards + rate table)
RESULT: all checks passed
```

### 遗留

- P8 剩余项：接入管理 `/integrations`（MCP 部署与统计）。
- 采集速率的历史曲线（多快照时序）未做——当前为实时快照。

---

## 阶段 P8e · 接入管理（P8 收官）

状态：**已完成 ✔**
开始：2026-09-14
完成：2026-09-14
依据：`UPGRADE-PLAN-v4.md` §4.6（接入管理）

### 交付

| 件 | 位置 | 说明 |
|---|---|---|
| 管理面端点 | `GET /api/v1/mcp/stats` | 近 N 天调用统计（审计聚合）+ 鉴权/工具数；时间窗口 Python 侧过滤（SQLite 无时区，字符串比较不可靠） |
| 协议自检 | `POST /api/v1/mcp/selftest` | 走真实协议层发 `initialize`——不伪造凭据（握手本身免鉴权，鉴权只在 tools/call） |
| 接入页 | `frontend/src/pages/Integrations.tsx` | 端点卡 + 配置片段（token 占位符）+ 测试连通 + 工具清单 + 调用统计 + 最近调用（跳审计 `?action=mcp.`） |
| 审计页增强 | `Audit.tsx` | 支持 `?action=` URL 参数初始化过滤 |
| 入口 | 侧边栏「平台治理」新增「接入管理」 | |
| 测试 | `tests/integration/test_mcp_admin_api.py` | 3 个（契约 / 审计聚合 delta / selftest 握手） |
| 验证 | `scripts/verify_integrations_p8e.py` | 8 项断言 + fail-closed 实证 + 截图 |

### 验收（实机门禁 8/8，证据 `docs/evidence/p8e-integrations/`）

```
OK  mcp overview (protocol + tools + auth)  --  tools=7 auth=False
OK  selftest initialize handshake  --  server=webinsight-agent 3.0.0 · 0.01ms
OK  unauthenticated tool call rejected (fail-closed)  --  error_code=-32001
OK  rejection is audited  --  total 0 -> 1 denied=1
OK  integrations page renders / selftest button E2E
RESULT: all checks passed
```

### 平台治理四页收官

| 页面 | 状态 |
|---|---|
| 合规中心 `/compliance` | ✅ P8a |
| 审计日志 `/audit` | ✅ P8b |
| 运行监视 `/monitor` | ✅ P8d |
| 接入管理 `/integrations` | ✅ **本阶段** |

P8 阶段全部完成。遗留：采集速率历史曲线、审计点补全（采集/物化/导出）。

---

## 阶段 P9a · 数据集检索与对比（P9 第一刀）

状态：**已完成 ✔**
开始：2026-09-14
完成：2026-09-14
依据：`UPGRADE-PLAN-v4.md` §3.2（D4 检索层 + A1 多数据集对比）

### 交付

| 件 | 位置 | 说明 |
|---|---|---|
| 检索 | `GET /collect/datasets/{id}/search` | 关键字（前 8 字段 OR LIKE 匹配）+ 字段限域；列名白名单校验 + 参数绑定防注入 |
| 对比 | `GET /collect/datasets/diff` | 行数差 / 共同字段 / 双向独有字段 / 类型变化 / 覆盖变化 |
| 列表 | `GET /collect/datasets` | 数据集元数据列表（对比选择器数据源） |
| 详情页检索 | `DatasetDetail.tsx` | 字段选择器 + 关键字框 + 检索/清除 + 命中计数 |
| 对比页 | `frontend/src/pages/Compare.tsx` | 双选择器 → 概览双卡（行数差徽章）+ 字段变化 + 覆盖变化 |
| 导航 | 数据资产组新增「对比分析」 | |
| 测试 | `tests/integration/test_dataset_search_diff.py` | 7 个（关键词 / 限域 / 非法字段 / 404 / diff / 列表契约） |
| 验证 | `scripts/verify_p9_datasetops.py` | 9 项断言 + 双截图 |

### 发现的设计事实（非缺陷）

重复采集同一静态站点 → 三级去重按设计跳过全部已知条目 → 新 job 零条目、
不产生新数据集（"增量优先"的正确语义）。版本对比的真实场景：
① 站点内容更新后的两次采集 ② 同源重新物化快照。

### 验收（实机门禁 9/9，证据 `docs/evidence/p9-datasetops/`）

```
OK  datasets list endpoint / two datasets available  --  ids=[2, 1]
OK  search keyword matches  --  total 1 -> 1 (q=Example)
OK  search no-match returns empty  --  total=0
OK  diff computes common fields  --  common=1 delta=0
OK  compare page renders diff result / dataset detail search E2E
RESULT: all checks passed
```

### 遗留

- P9 剩余：D2 显式快照版本链、D3 保留策略、D4 检索深化（多关键字 / 全文索引）。
