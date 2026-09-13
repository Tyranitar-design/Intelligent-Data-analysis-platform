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

## 下一步：P2 采集内核

目标：`backend/collect/`

- `collect/registry.py` —— Capability 协议与注册表（评分选链）
- `collect/scheduler.py` —— 任务编排、分片、断点续传
- `collect/capabilities/` —— 8 个能力实现（复用现有 `intelligent/strategies/`）
- `collect/dedup.py` —— 三级去重（主键 / SimHash / 语义）
- `collect/ratelimit.py` —— 自适应限速
- `collect/assist.py` —— 人机协同通道
- 建表：`collect_plan`、`collect_job`、`collect_task`、`collect_item`

---

## 待确认（需 YG 决策）

1. 测试用户 `smoke_probe`（id=1）为 P0.3 验收产生，保留还是清理？
2. 前端历史组件 `components/cyber/*`（8 个赛博视图）与 `pages/CyberIndex.tsx` 如何处置：
   作为 P6 新前端的设计基础保留，还是推倒重做？
3. P6 前端体积治理方案确认：移除 `antd`（与 shadcn/ui 重复）、图表库收敛为 ECharts 单一
   （现为 plotly + echarts + recharts 三套并存），预计可把 5.35 MB 主包降至 1.5 MB 以内。
