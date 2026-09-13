# 🗄️ 智能数据分析平台 - 数据库配置指南

> 配置更新日期: 2026-04-27
> 更新内容: 统一数据库配置，添加 ClickHouse 和 Kafka

---

## 📋 数据库架构

```
┌─────────────────────────────────────────────────────────────┐
│                    智能数据分析平台 v1.5                      │
├─────────────────────────────────────────────────────────────┤
│  前端 (React)  →  Nginx  →  FastAPI / Django               │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL (OLTP)  │  ClickHouse (OLAP)  │  Redis        │
├─────────────────────────────────────────────────────────────┤
│  Kafka (Redpanda)   │  MongoDB            │  MinIO        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🐘 PostgreSQL (主数据库)

### 用途
- 用户数据
- 业务数据
- 元数据存储

### 配置
```yaml
# docker-compose.yml
postgres:
  image: postgres:15
  environment:
    POSTGRES_DB: data_platform
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
  ports:
    - "5432:5432"
```

### 连接信息
- **主机**: localhost (或 postgres)
- **端口**: 5432
- **数据库**: data_platform
- **用户**: postgres
- **密码**: postgres

### 环境变量
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/data_platform
```

---

## 🚀 ClickHouse (OLAP 数据库)

### 用途
- 事件分析
- 时序数据
- 大数据查询

### 配置
```yaml
# docker-compose.yml
clickhouse:
  image: clickhouse/clickhouse-server:26.3.9.8
  ports:
    - "8123:8123"  # HTTP 接口
    - "9000:9000"  # 原生接口
```

### 连接信息
- **主机**: localhost (或 clickhouse)
- **HTTP 端口**: 8123
- **原生端口**: 9000
- **数据库**: data_platform
- **用户**: default

### 环境变量
```bash
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_DB=data_platform
```

### Python 客户端
```python
from clickhouse_client import ClickHouseClient

client = ClickHouseClient()

# 查询
result = client.query("SELECT * FROM events LIMIT 10")

# 插入
client.insert('events', [
    {'event_type': 'click', 'user_id': '123'},
    {'event_type': 'view', 'user_id': '456'}
])
```

---

## 📨 Kafka (消息队列)

### 用途
- 事件流处理
- 数据管道
- 实时分析

### 配置
```yaml
# docker-compose.yml
kafka:
  image: redpandadata/redpanda:v25.1.9
  ports:
    - "9092:9092"  # Kafka 端口
    - "9644:9644"  # Redpanda 管理端口
```

### 连接信息
- **主机**: localhost (或 kafka)
- **端口**: 9092
- **外部端口**: 19092

### 环境变量
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Python 客户端
```python
from kafka_client import KafkaClient

client = KafkaClient()

# 发送事件
client.send('events', {
    'event_type': 'click',
    'user_id': '123',
    'data': {'page': '/home'}
})

# 消费消息
messages = client.consume(['events'], max_messages=10)
```

---

## ⚡ Redis (缓存)

### 用途
- 会话缓存
- 速率限制
- 任务队列

### 配置
```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

### 连接信息
- **主机**: localhost (或 redis)
- **端口**: 6379

### 环境变量
```bash
REDIS_URL=redis://localhost:6379/0
```

---

## 🍃 MongoDB (文档数据库)

### 用途
- 非结构化数据
- 日志存储
- 临时数据

### 配置
```yaml
# docker-compose.yml
mongodb:
  image: mongo:6
  ports:
    - "27017:27017"
```

### 连接信息
- **主机**: localhost (或 mongodb)
- **端口**: 27017
- **用户**: admin
- **密码**: admin123

### 环境变量
```bash
MONGO_URL=mongodb://admin:admin123@localhost:27017
```

---

## 🪣 MinIO (对象存储)

### 用途
- 文件存储
- 模型存储
- 备份存储

### 配置
```yaml
# docker-compose.yml
minio:
  image: minio/minio
  ports:
    - "9000:9000"   # API 端口
    - "9001:9001"   # 控制台端口
```

### 连接信息
- **主机**: localhost (或 minio)
- **API 端口**: 9000
- **控制台**: http://localhost:9001
- **用户**: admin
- **密码**: admin123456

---

## 🚀 快速开始

### 1. 启动所有服务

```bash
# 进入项目目录
cd D:\智能数据分析平台

# 启动所有数据库服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 2. 测试连接

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt

# 运行测试
python test_db_connection.py
```

### 3. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
notepad .env
```

---

## 📊 服务端口速查

| 服务 | 端口 | 用途 |
|------|------|------|
| PostgreSQL | 5432 | 主数据库 |
| ClickHouse | 8123/9000 | OLAP 数据库 |
| Kafka | 9092/19092 | 消息队列 |
| Redis | 6379 | 缓存 |
| MongoDB | 27017 | 文档数据库 |
| MinIO | 9000/9001 | 对象存储 |
| Kafka UI | 8080 | Kafka 管理界面 |

---

## 🔧 故障排除

### PostgreSQL 连接失败

```bash
# 检查服务状态
docker-compose ps postgres

# 查看日志
docker-compose logs postgres

# 重启服务
docker-compose restart postgres
```

### ClickHouse 连接失败

```bash
# 检查服务状态
docker-compose ps clickhouse

# 测试连接
curl http://localhost:8123/ping
```

### Kafka 连接失败

```bash
# 检查服务状态
docker-compose ps kafka

# 查看主题
docker exec -it kafka rpk topic list
```

---

## 📚 相关文档

- [PostgreSQL 文档](https://www.postgresql.org/docs/)
- [ClickHouse 文档](https://clickhouse.com/docs)
- [Redpanda 文档](https://docs.redpanda.com)
- [Redis 文档](https://redis.io/documentation)
- [MongoDB 文档](https://docs.mongodb.com)
- [MinIO 文档](https://docs.min.io)

---

## 📝 更新日志

### 2026-04-27
- ✅ 统一 PostgreSQL 配置
- ✅ 添加 ClickHouse 服务
- ✅ 添加 Kafka (Redpanda) 服务
- ✅ 创建数据库测试脚本
- ✅ 创建 Python 客户端封装

---

*数据库配置已更新 | 请运行测试验证* 🎉
