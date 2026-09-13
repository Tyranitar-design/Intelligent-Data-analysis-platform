# Tasks: 企业级重构 v2.0

## Phase 1: 基础设施 (Week 1-2)

### Week 1

- [ ] **Task 1.1**: 项目结构重构
  - 创建新的目录结构
  - 分离前端/后端/部署配置
  - 设置 monorepo 或独立仓库

- [ ] **Task 1.2**: Docker 化
  - 编写 Dockerfile (前端 + 后端)
  - 编写 docker-compose.yml
  - 配置环境变量管理

- [ ] **Task 1.3**: 数据库设计
  - 设计核心表结构
  - 编写 Alembic 迁移脚本
  - 配置数据库连接池

### Week 2

- [ ] **Task 1.4**: API 框架搭建
  - FastAPI 项目脚手架
  - 统一响应格式
  - 全局异常处理
  - CORS 配置

- [ ] **Task 1.5**: 前端基础架构
  - Vite + React + TypeScript 项目
  - Tailwind CSS 配置
  - shadcn/ui 初始化
  - 路由配置

- [ ] **Task 1.6**: 认证系统
  - JWT 实现
  - 登录/注册页面
  - 权限中间件

## Phase 2: 采集系统 (Week 3-4)

### Week 3

- [ ] **Task 2.1**: Scrapling 集成
  - 安装 Scrapling 依赖
  - 封装 Scrapling 适配器
  - 测试反爬绕过

- [ ] **Task 2.2**: 分布式爬虫引擎
  - Celery 配置
  - 任务队列设计
  - Worker 实现
  - 并发控制

- [ ] **Task 2.3**: robots.txt 合规
  - 实现 robots.txt 解析
  - 爬取前检查逻辑
  - 用户提示

### Week 4

- [ ] **Task 2.4**: API 适配器框架
  - 适配器基类设计
  - 预置 5 个金融数据源
  - 配置化管理

- [ ] **Task 2.5**: 用户自定义采集
  - 采集配置表单
  - 配置验证
  - 测试运行

- [ ] **Task 2.6**: 本地文件导入
  - CSV/Excel/JSON 解析
  - 数据预览
  - 字段类型推断

## Phase 3: 分析系统 (Week 5-6)

### Week 5

- [ ] **Task 3.1**: EDA 模块
  - 统计描述
  - 相关性分析
  - 可视化图表

- [ ] **Task 3.2**: ML Pipeline
  - 数据预处理
  - 模型训练
  - 模型评估
  - 结果保存

### Week 6

- [ ] **Task 3.3**: DL Pipeline
  - NLP 任务
  - 时序预测
  - GPU 支持

- [ ] **Task 3.4**: 数据挖掘
  - 关联规则
  - 异常检测

## Phase 4: 前端重构 (Week 7-8)

### Week 7

- [ ] **Task 4.1**: 核心页面开发
  - 工作台
  - 数据采集
  - 数据集管理

- [ ] **Task 4.2**: 可视化组件
  - 图表库集成
  - 交互式图表
  - 仪表盘布局

### Week 8

- [ ] **Task 4.3**: 模型管理页面
  - 训练任务
  - 模型列表
  - 评估结果

- [ ] **Task 4.4**: 报告中心
  - 报告模板
  - 预览/导出
  - 历史记录

## Phase 5: 企业级特性 (Week 9-10)

### Week 9

- [ ] **Task 5.1**: 监控
  - Prometheus 指标
  - Grafana 仪表盘
  - 告警规则

- [ ] **Task 5.2**: 性能优化
  - Redis 缓存
  - 数据库优化
  - 前端优化

### Week 10

- [ ] **Task 5.3**: 安全加固
  - HTTPS
  - 数据加密
  - 审计日志

- [ ] **Task 5.4**: 文档与部署
  - API 文档
  - 部署指南
  - 用户手册

---

*Tasks | 2026-05-07*
