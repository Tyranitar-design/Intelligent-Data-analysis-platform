# MCP 接入部署（P10 · O2）

> 目标：把 WebInsight 的 MCP 工具面（`POST /mcp`）部署到目标运行环境，
> 供 Hermes 等 MCP 客户端调用。本包 = **配置模板 + 部署步骤 + 校验命令**。
>
> 诚实标注：本机已验证部分见 §六；**云端（Lite 形态）执行待环境就绪后进行**。

## 一、双部署形态（引用 `docs/REBUILD-SPEC-v3.md`）

| 形态 | 环境 | MCP 面 |
|---|---|---|
| Full | 本机 Windows | 全量能力 + MCP |
| Lite | 云服务器 | 采集与存储优先；不部署前端 / MinIO / ClickHouse |

## 二、部署步骤（Lite 形态示例）

1. 代码到达服务器（`git clone` 或 rsync 投递）
2. Python 环境：`python -m venv venv && venv/bin/pip install -r backend/requirements-v2.txt`
3. 配置 `backend/.env`：

   ```env
   DATABASE_URL=sqlite:///./data_platform.db
   MCP_API_KEY=<TOKEN>:hermes          # 格式：token:principal；多组用逗号分隔
   SCHEDULE_TICK_SECONDS=15
   ```

   ⚠ token 只进环境变量 / `.env`——不提交、不写进文档、不进审计。

4. 启动：`venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000`
   （生产建议 systemd 单元或现有 Dockerfile）
5. 反向代理（可选）：nginx 转发 `/mcp`，保持 `Authorization` 头透传

## 三、校验命令

```bash
curl -s http://127.0.0.1:8000/health                     # 服务健康
curl -s http://127.0.0.1:8000/mcp                        # 协议概览（工具清单）
curl -s -X POST http://127.0.0.1:8000/api/v1/mcp/selftest # 协议自检（initialize 握手）
```

## 四、Hermes 侧接入

1. 依 `mcp-client-config.example.json` 填 `url`（服务器地址）与 `Authorization`（部署配置的 token）
2. 接入后先 `tools/list` 确认 7 个工具可见
3. 用 `analyze_site` 做一次端到端调用验证（会写入审计）

## 五、安全边界

- 本包不含任何真实 token（占位符 `<MCP_API_KEY>`）；
- MCP 端点 **fail-closed**：未配置 token 时拒绝一切需要鉴权的调用；
- 每次工具调用与拒绝均写 `audit_logs`（可在 `/integrations` 页观测）。

## 六、已验证清单（本机 · 2026-09-14）

- [x] 协议自检 initialize 握手（`verify_integrations_p8e.py`：0.01ms）
- [x] fail-closed 实证（无凭据调用 → `-32001` + 审计留痕）
- [x] 工具清单 7 个（`/mcp` 概览）
- [x] 调用统计聚合（`/api/v1/mcp/stats`）
- [x] 接入管理页（配置片段 / 测试连通 / 调用统计）
- [ ] **云端部署执行**——待 Lite 形态环境就绪后按本包执行并回填结果
