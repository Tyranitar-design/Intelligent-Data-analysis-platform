# Phase 4: 前端重构提案

**日期**: 2026-05-08
**状态**: 待批准
**变更**: `enterprise-refactor/phase4-frontend`

---

## 1. 目的

将前端从"双套UI并存+硬编码假数据"状态，重构为"统一shadcn/ui界面+全量对接Phase 2/3后端"的企业级前端。

## 2. 用户故事

- 作为数据分析师，我想要在Web界面上一键采集数据，以便快速获取分析素材
- 作为数据分析师，我想要在界面上运行EDA/ML/DL/挖掘分析，以便无需写代码即可完成数据分析
- 作为数据分析师，我想要查看和导出分析报告，以便分享分析成果
- 作为管理员，我想要管理数据源和爬虫任务，以便控制数据采集流程

## 3. 功能需求

### 3.1 MUST (必须有)

- [ ] **API 服务层重构**: 全面对接 Phase 2(11爬虫端点) + Phase 3(EDA/ML/DL/Mining/Report)
- [ ] **统一路由**: 废弃 CyberIndex 硬路由，采用 App-v2 shadcn 路由结构
- [ ] **仪表盘页**: 真实数据统计 + 最近任务 + 快捷操作
- [ ] **数据源页**: 展示7个适配器状态，一键采集
- [ ] **采集管理页**: 任务创建/启动/停止/进度 + Celery状态
- [ ] **EDA 分析页**: 数据上传 → 一键EDA → 质量评分 + 缺失值建议 + 图表
- [ ] **ML 训练页**: 算法选择 → 参数配置 → 训练 → 评估结果 + 特征重要性
- [ ] **数据挖掘页**: 关联规则 + 异常检测 + 降维可视化
- [ ] **报告中心页**: 自动报告生成 + Markdown/HTML 预览 + 导出
- [ ] **全局状态管理**: Zustand store (任务状态/分析结果/通知)
- [ ] **响应式布局**: 移动端可用

### 3.2 SHOULD (应该有)

- [ ] **赛博朋克主题**: dark mode 下保留赛博朋克视觉风格
- [ ] **DL 训练页**: 时序预测 + NLP 情感分析
- [ ] **可视化页**: 10种图表交互式生成
- [ ] **数据集管理**: 上传/预览/删除

### 3.3 COULD (可以有)

- [ ] **实时 WebSocket**: 任务进度推送
- [ ] **设置页**: API Key 管理 + 主题切换

## 4. 技术方案

### 4.1 架构

```
src/
├── api/                    # API 服务层 (新)
│   ├── client.ts          # axios 实例 + 拦截器
│   ├── crawl.ts           # 爬虫相关 API
│   ├── analysis.ts        # EDA + 特征工程 API
│   ├── ml.ts              # ML Pipeline API
│   ├── dl.ts              # DL Pipeline API
│   ├── mining.ts          # 数据挖掘 API
│   └── report.ts          # 报告 API
├── stores/                # Zustand 全局状态 (新)
│   ├── appStore.ts        # 全局状态 (侧边栏/通知)
│   ├── taskStore.ts       # 任务状态
│   └── analysisStore.ts   # 分析结果缓存
├── pages/                 # 页面 (重构)
│   ├── Dashboard.tsx
│   ├── DataSource.tsx
│   ├── Crawl.tsx
│   ├── Analysis.tsx       # EDA + 特征工程
│   ├── ML.tsx             # ML Pipeline
│   ├── DL.tsx             # DL Pipeline
│   ├── Mining.tsx         # 数据挖掘
│   ├── Visualization.tsx
│   ├── Reports.tsx
│   └── Settings.tsx
├── components/
│   ├── layout/            # 布局组件
│   ├── ui/                # shadcn/ui (保留)
│   ├── charts/            # 图表组件 (新)
│   └── analysis/          # 分析专用组件 (新)
└── hooks/                 # 自定义 hooks (新)
```

### 4.2 图表策略

| 库 | 用途 | 保留 |
|---|------|------|
| **Recharts** | 基础图表 (line/bar/pie/scatter) | ✅ |
| **Plotly** | 高级交互 (3D/heatmap/violin) | ✅ |
| **ECharts** | — | ❌ 移除(冗余) |

### 4.3 状态管理

```typescript
// Zustand Store 结构
interface AppStore {
  // 全局
  sidebarOpen: boolean
  notifications: Notification[]
  
  // 任务
  tasks: CrawlTask[]
  taskResults: Map<string, any>
  
  // 分析
  datasets: Dataset[]
  edaResults: Map<string, EDAResult>
  mlModels: MLModel[]
  
  // 操作
  addNotification: (n: Notification) => void
  fetchTasks: () => Promise<void>
  // ...
}
```

### 4.4 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| React | 18.2 | 核心 |
| shadcn/ui | 已有 | 组件库 |
| Zustand | 4.5 | 状态管理 |
| Recharts | 3.8 | 基础图表 |
| Plotly | 2.29 | 高级图表 |
| @tanstack/react-query | 新增 | 服务端状态缓存 |
| framer-motion | 12.x | 动画 |

## 5. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 页面复杂度高 | 开发周期长 | 分5个Task逐步推进 |
| CyberIndex删除 | 丢失赛博朋克UI | 保留CSS变量，dark mode复用 |
| 后端接口未启动 | 前端无法测试 | Mock数据 + 错误边界 |
| 移除ECharts | 现有代码依赖 | 先检查引用再移除 |

## 6. 测试策略

- 每个页面完成后手动验证
- API 层编写类型测试
- 最终: `npm run build` 零错误

## 7. 任务分解

### Task 4.1: API 服务层 + 全局状态 (P0)
- 创建 `api/client.ts` (axios 实例 + 拦截器)
- 创建分模块 API 文件 (crawl/analysis/ml/dl/mining/report)
- 创建 Zustand stores (app/task/analysis)
- 移除旧 `services/api.ts`
- 添加 @tanstack/react-query

### Task 4.2: 布局 + 仪表盘 + 数据源 (P0)
- 启用 App-v2 路由结构
- 重构 Sidebar (增加新页面导航)
- Dashboard 真实数据统计
- DataSource 7适配器状态展示

### Task 4.3: 采集 + EDA + ML 页面 (P0)
- Crawl 页面: 任务CRUD + 进度
- Analysis 页面: 数据上传 + EDA引擎
- ML 页面: 训练 + 评估 + 特征重要性

### Task 4.4: DL + 挖掘 + 可视化 + 报告 (P1)
- DL 页面: 时序 + NLP
- Mining 页面: 关联规则 + 异常 + 降维
- Visualization 页面: 图表生成器
- Reports 页面: 报告生成 + 预览 + 导出

### Task 4.5: 主题 + 响应式 + 清理 (P1)
- 赛博朋克 dark mode CSS 变量
- 移动端响应式
- 移除 CyberIndex + 旧 App.tsx
- 移除 echarts
- `npm run build` 零错误
