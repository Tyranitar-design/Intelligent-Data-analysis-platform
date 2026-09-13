# 📊 智能数据分析平台

> 集数据采集、智能分析、预测建模、可视化展示于一体的综合性数据分析平台

---

## 🎯 项目概述

| 特性 | 说明 |
|------|------|
| **数据采集** | Scrapy + Playwright 多源爬虫 |
| **数据分析** | EDA + 统计分析 + 可视化 |
| **机器学习** | 分类、回归、聚类、预测 |
| **深度学习** | NLP、时间序列、推荐系统 |
| **数据挖掘** | 关联规则、异常检测 |
| **全栈开发** | React + FastAPI + Django |

---

## 🏗️ 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design |
| 后端 API | FastAPI |
| 后端 Admin | Django 5 |
| 数据库 | PostgreSQL + Redis + MongoDB + MinIO |
| 爬虫 | Scrapy + Playwright |
| ML/DL | scikit-learn + PyTorch + Transformers |
| 部署 | Docker + Docker Compose |

---

## 🚀 快速开始

### 1. 启动数据库服务

```bash
docker compose up -d postgres redis mongodb minio
```

### 2. 启动后端 API

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.api.main:app --reload --port 8000

PS D:\智能数据分析平台\backend> venv\Scripts\activate
(venv) PS D:\智能数据分析平台\backend> python.exe run_api.py
```

### 3. 启动 Django Admin

```bash
cd backend/admin
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8001
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 5. 一键启动（Docker）

```bash
docker compose up -d
```

---

## 📂 项目结构

```
intelligent-data-platform/
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── components/          # 组件
│   │   ├── pages/               # 页面
│   │   ├── services/            # API 服务
│   │   └── App.tsx              # 路由配置
│   └── package.json
│
├── backend/                     # 后端服务
│   ├── api/                     # FastAPI 服务
│   │   ├── routers/             # 路由（crawl, analysis, ml, reports）
│   │   └── main.py              # 入口文件
│   │
│   ├── admin/                   # Django Admin
│   │   ├── apps/                # Django Apps
│   │   └── settings/            # 配置
│   │
│   ├── crawlers/                # 爬虫模块
│   ├── ml/                      # 机器学习模块
│   ├── analysis/                # 数据分析模块
│   └── reports/                 # 报告模块
│
├── docker/                      # Docker 配置
├── data/                        # 数据目录
├── docker-compose.yml           # Docker Compose
├── DESIGN.md                    # 设计文档
└── README.md                    # 项目说明
```

---

## 📡 API 文档

启动后端后访问：
- FastAPI 文档: http://localhost:8000/docs
- Django Admin: http://localhost:8001/admin

---

## 📋 开发进度

### Phase 1: MVP ✅
- [x] 项目初始化 + 目录结构
- [x] FastAPI 基础 API
- [x] Django Admin 基础
- [x] React 前端框架
- [x] Docker 环境配置

### Phase 2: 核心功能 ⏳
- [ ] 电商数据爬虫
- [ ] 数据分析模块
- [ ] 机器学习模块
- [ ] 前端页面完善

### Phase 3: 高级功能 ⏳
- [ ] 深度学习模块
- [ ] 数据挖掘模块
- [ ] 自动化报告
- [ ] 性能优化

---

## 👥 团队

| 成员 | 角色 |
|------|------|
| 小宇 | 项目负责人 💼 |
| 小彩 | 项目管家 🏠 |
| CodeBuddy Code | 代码专家 💻 |

---

_智能数据分析平台 © 2026 | 小彩制作 💫_