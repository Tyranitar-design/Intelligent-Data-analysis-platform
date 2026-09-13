# 智能数据分析平台 v2.0

> 企业级智能数据分析平台 - 集数据采集、智能分析、预测建模、可视化展示于一体

---

## 技术架构

### 后端
- **FastAPI** - 高性能异步 Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **Celery** - 分布式任务队列
- **PostgreSQL** - 主数据库
- **Redis** - 缓存与消息队列
- **MinIO** - 对象存储

### 前端
- **React 18** + **TypeScript**
- **Tailwind CSS** - 原子化 CSS
- **shadcn/ui** - 组件库
- **TanStack Query** - 服务端状态管理
- **Zustand** - 客户端状态管理

### 数据采集
- **Scrapling** - 新一代爬虫框架（反爬绕过）
- **httpx** - 异步 HTTP 客户端
- **aiohttp** - 异步 Web 框架

### 数据分析
- **Pandas / NumPy** - 数据处理
- **scikit-learn** - 机器学习
- **PyTorch** - 深度学习
- **XGBoost** - 梯度提升

---

## 快速开始

### 环境要求
- Windows PowerShell
- Python 3.11+
- Node.js 20+
- Docker Desktop（可选，仅用于后续容器联调）

### 推荐：本地开发主线

当前推荐的 canonical 开发路径是“本地开发优先”，不是先上 Docker。

#### 首次准备

**后端：**
```powershell
cd D:\智能数据分析平台\backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-v2.txt
Copy-Item .env.example .env -ErrorAction SilentlyContinue
```

说明：
- 如果你已经有本地可用的 `backend\.env`，不会覆盖。
- 本地开发默认可以直接使用 SQLite：
  `DATABASE_URL=sqlite:///./data_platform.db`

**前端：**
```powershell
cd D:\智能数据分析平台\frontend
npm install
```

#### 一键启动

在项目根目录执行：

```powershell
cd D:\智能数据分析平台
.\run-dev.cmd
```

可用命令：

```powershell
.\run-dev.cmd start
.\run-dev.cmd check
.\run-dev.cmd status
.\run-dev.cmd stop
```

启动后默认地址：
- 前端: http://127.0.0.1:5173
- 后端: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- 能力状态: http://127.0.0.1:8000/capabilities

#### 当前后端主线说明

- 当前 `api.main` 是轻量主 API，优先承载产品主链：
  `auth / crawl / analysis / data / reports`
- `ml / dl / mining` 保留在代码库中，并按当前环境可用性动态挂载
- 这样可以先稳定主平台运行链，再逐步收敛重模块

### Docker v2（后续联调 / 部署用）

当需要做容器联调时，再使用 Docker：

```powershell
cd D:\智能数据分析平台
$env:COMPOSE_PROJECT_NAME="idp"
docker compose -f docker-compose-v2.yml up -d

docker compose -f docker-compose-v2.yml logs -f
docker compose -f docker-compose-v2.yml down
```

---

## 项目结构

```
.
├── backend/                 # 后端代码
│   ├── api/                 # API 层
│   │   ├── core/            # 核心配置
│   │   ├── models/          # 数据模型
│   │   ├── routers/         # 路由
│   │   ├── schemas/         # Pydantic 模型
│   │   └── tasks/           # Celery 任务
│   ├── crawlers/            # 爬虫模块
│   ├── analysis/            # 分析模块
│   ├── ml/                  # 机器学习模块
│   └── requirements-v2.txt  # 依赖
├── frontend/                # 前端代码
│   ├── src/
│   │   ├── components/      # 组件
│   │   │   └── ui/          # shadcn/ui 组件
│   │   ├── pages/           # 页面
│   │   ├── lib/             # 工具函数
│   │   └── App.tsx          # 应用入口
│   └── package.json         # 依赖
└── docker-compose-v2.yml    # Docker 编排
```

---

## 核心功能

### 1. 数据采集
- [x] API 数据采集（RESTful API）
- [x] 网页爬取（Scrapling 反爬绕过）
- [x] 本地文件导入（CSV/Excel/JSON）
- [x] 分布式采集（Celery）
- [x] robots.txt 合规检查

### 2. 数据分析
- [x] 探索性分析（EDA）
- [x] 统计分析
- [x] 数据可视化

### 3. 机器学习
- [x] 分类 / 回归 / 聚类
- [x] 自动超参调优
- [x] 模型评估与保存

### 4. 深度学习
- [x] NLP（文本分类、情感分析）
- [x] 时序预测

### 5. 数据挖掘
- [x] 关联规则
- [x] 异常检测

---

## API 文档

启动服务后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 监控

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

---

## 许可证

MIT License
