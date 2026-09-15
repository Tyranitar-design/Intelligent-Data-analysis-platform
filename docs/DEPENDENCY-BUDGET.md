# 依赖与体积预算表（v5 验收 5.1-2 / 5.1-9）

> 更新：2026-09-15 · 数据全部来自生产构建实测（`npm run build` + `scripts/verify_perf_budget.py`）

## 一、预算红线

| 项 | 上限 | 当前实测 | 守护 |
|---|---|---|---|
| 首屏 JS+CSS（gzip 合计） | **300KB** | **228.7KB** | `backend/scripts/verify_perf_budget.py` |
| 演示 GIF | 5MB | 4.14MB | `docs/assets/demo/demo.gif` |
| 图表引擎（echarts） | 不入首屏请求 | ✓ 随 `/analytics` 按需 | verify_perf_budget 项 4/6 |
| 展示岛星云（three.js） | 不入首屏请求 | ✓ 独立 lazy chunk | verify_perf_budget 项 2/5 |

## 二、首屏资源明细（生产构建实测）

| 资源 | 原始 | gzip | 说明 |
|---|---|---|---|
| `index-*.js`（入口） | 434.9KB | 128.6KB | 应用主体（页面 + 组件 + radix/ui） |
| `react-vendor-*.js` | 164.7KB | 52.4KB | react / react-dom / react-router-dom |
| `motion-vendor-*.js` | 96.2KB | 30.9KB | motion |
| `index-*.css` | 104.4KB | 16.8KB | Tailwind + 设计 tokens |
| **合计** | — | **228.7KB** | ✓ ≤ 300KB |

## 三、按需加载 chunk（不在首屏请求序列）

| chunk | 原始 | gzip | 触发时机 |
|---|---|---|---|
| `Analytics-*.js`（含 echarts） | 585.7KB | 196.4KB | 访问 `/analytics`（`React.lazy`） |
| `nebula-scene-*.js`（three.js） | 518.5KB | 130.2KB | 访问 `/showcase`（触发器级 `import()`） |

## 四、修复记录（2026-09-15，建档过程中的真实发现）

- **发现**：`dist/index.html` 曾 `modulepreload` `chart-vendor`（echarts 194.5KB gzip）——首屏实测合计 ≈431KB，**超 300KB 预算**。
- **根因**：`vite.config.ts` 的 `manualChunks: {'chart-vendor': ['echarts']}` 强制拆分 + `App.tsx` 对 Analytics 的静态 import → echarts 被拉进入口依赖图。
- **修复**（提交见 REBUILD-PROGRESS 依存记录）：
  1. `Analytics` 改 `React.lazy` + `Suspense`（路由级懒加载）；
  2. 移除 chart-vendor 强制拆分——echarts 的唯一使用方是 Analytics，自然随 lazy chunk 走即为最优拆分。
- **验证**：`verify_perf_budget.py` 8/8（preload 清单干净 + 真实首屏请求序列无 chart-vendor / nebula-scene + `/analytics` 按需加载 + 无 JS 异常）。

## 五、前端依赖清单（按用途）

| 类别 | 依赖 | 体积影响 |
|---|---|---|
| 框架 | react · react-dom · react-router-dom | react-vendor 52.4KB gzip |
| UI 原语 | @radix-ui/react-*（27 个）· clsx · cva · tailwind-merge | 按引用进主包（shadcn 模式） |
| 图标 | lucide-react | 按需 import，进主包 |
| 动效 | motion | motion-vendor 30.9KB gzip |
| 数据 / 状态 | @tanstack/react-query · zustand · axios | 进主包 |
| 表单 | react-hook-form · @hookform/resolvers | 进主包 |
| 图表 | **echarts** | 196.4KB gzip —— 仅 `/analytics` 按需 |
| 3D | **three** | 130.2KB gzip —— 仅 `/showcase` 按需 |
| 其他 UI | sonner · vaul · cmdk · react-resizable-panels · dayjs | 进主包 |

## 六、后端依赖清单（`backend/requirements-v2.txt`）

| 类别 | 依赖 | 说明 |
|---|---|---|
| Web / 认证 | fastapi · uvicorn · python-multipart · python-jose · bcrypt | API + 认证（bcrypt 直用，不经 passlib） |
| 数据 | sqlalchemy · psycopg2-binary · alembic · redis · pymongo | ORM / 迁移 / 缓存 |
| 队列 | celery · flower | 异步任务 |
| 处理 | pandas · numpy · scipy · openpyxl · pyarrow | 数据管道 |
| ML / DL | scikit-learn · xgboost · lightgbm · optuna · torch · transformers · datasets | 可选路由（依赖缺失自动 disabled） |
| 可视化 | matplotlib · plotly · seaborn | 报告图表 |
| 采集 | scrapling[all] · httpx · aiohttp · fake-useragent | 反爬链 |
| 挖掘 | mlxtend · pyod | Apriori / 异常检测 |
| 报告 | jinja2 · python-docx · weasyprint | 生成链 |

## 七、新增依赖准入规则

1. **先查体积**：评估 gzip 量级；单依赖进主包 >30KB 必须给出理由，>50KB 必须可懒加载。
2. **先查替代**：shadcn 模式优先——复制源码而非加运行时依赖。
3. **先查拆分**：重依赖必须绑定懒加载路径（路由级 `React.lazy` 或触发器级 `import()`）。
4. **登记**：准入后更新本表；`verify_perf_budget.py` 作为回归红线。

## 八、复查命令

```powershell
cd frontend
npm run build

cd ..\backend
.\venv\Scripts\python.exe scripts\verify_perf_budget.py    # 预算门禁（8 项）
```
