# 重建进度记录

> 每完成一个阶段在此追加：阶段号 / 完成项 / 验收命令 / 实测输出 / 遗留问题。
> 依据：`docs/REBUILD-SPEC-v3.md` 与 `docs/HERMES-PROMPT-v3.md`。

---

## 阶段 P0 · 收敛与基线治理

状态：**进行中**
开始：2026-09-14

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

### 待办

- [ ] **P0.4** 消除同名模块/包冲突（Python 导入歧义）
- [ ] **P0.5** 删除重复入口
- [ ] **P0.6** 测试归位
- [ ] **P0.7** 文档收敛
- [ ] **P0.8** 无关文件处理

### 待确认（需 YG 决策）

1. 测试用户 `smoke_probe`（id=1）为 P0.3 验收产生，保留还是清理？
2. `backend/alns_vrptw_*.py` 五个 VRP 求解器文件与数据采集平台无关，疑似其他项目误入，
   是否移出本项目？
