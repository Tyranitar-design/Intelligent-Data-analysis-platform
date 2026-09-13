## Context

`D:\智能数据分析平台` 当前已经形成了较完整的数据主链：

- `crawl`
  - `robots-check`
  - `url/probe`
  - `url/crawl`
  - `smart/v2/probe`
  - `smart/v2/crawl`
  - `smart/extract`
  - `auth/login`
  - `auth/cookie`
  - `auth/status`
- `datasets`
  - 保存与读取结构化数据
- `analysis`
  - EDA 与数据集分析
- `reports`
  - 基于真实数据表生成报告

但这些能力目前更像“已经存在的一组能力点”，而不是“一个产品内可控、可复盘、可重复的验收系统”。同时，登录态 / 验证码站点的测试需求已经出现，且用户明确希望采用合规的人机协同方式，而不是自动绕过验证码。

项目现有规范已经提供两个重要约束：

- `harness-engineering`
  要求清晰接口边界、类型化模型、标准错误格式、显式状态
- `vibe-coding`
  要求操作员读得懂的状态、明确的人工检查点、低认知负担的结果呈现

## Goals / Non-Goals

**Goals:**

- 在平台内提供一个独立的 `Smoke Center / 验收中心`
- 将 smoke 设计为编排层，复用现有 crawl/auth/analysis/reports 能力，而不是复制一套子系统
- 提供三层场景：
  - `local`
  - `live-public`
  - `live-assisted`
- 将 `Bilibili` 作为首个 assisted-auth 验证平台
- 把 assisted-auth 设计成通用框架，后续可扩展到知乎、微博、豆瓣、小红书和自定义站点
- 将 `robots.txt` 结果、采集策略、人工介入、数据集保存、Analysis 和 Reports 统一成一个结构化 smoke 结果模型
- 提供实现前计划，以阶段化执行降低返工

**Non-Goals:**

- 不自动破解验证码
- 不自动绕过站点安全防护
- 不在本 change 中完成所有平台的 assisted-auth 实装
- 不在本 change 中完成 Docker、SSE/WebSocket 或分布式 smoke 扩展
- 不重写现有 crawl/auth/analysis/reports 核心能力，只做编排与产品集成

## Decisions

### 1. Smoke Center 作为编排层，而不是平行系统

**Decision**
- 新建独立 `smoke` 路由与服务模块
- 复用现有：
  - `crawl`
  - `auth`
  - `dataset_service`
  - `analysis`
  - `reports`

**Rationale**
- 当前项目已经有大量现成能力
- 若再复制一套 smoke 专属 crawl/auth 逻辑，会加重分叉和维护成本
- 编排层更符合 harness engineering 的“清晰边界 + 单一职责”

**Alternatives considered**
- 直接在 `crawl.py` 里追加 smoke 逻辑
  - 被拒绝：`crawl.py` 已经过大、职责过多
- 只做命令行脚本，不做产品集成
  - 被拒绝：用户明确希望能力集成到项目并且前端可控

### 2. 场景注册表优先于硬编码流程

**Decision**
- 引入 `scenario registry`
- 每个场景定义：
  - `scenario_id`
  - `mode`
  - `target_url`
  - `requires_robots_check`
  - `requires_auth`
  - `requires_human`
  - `preferred_strategy`
  - `post_steps`

**Rationale**
- 首先验证 `Bilibili`
- 但目标是泛化到任意 assisted-auth 平台
- 场景注册比硬编码平台分支更利于后续扩展

**Alternatives considered**
- 每个平台单独写一套流程
  - 被拒绝：会快速膨胀，不利于规范化

### 3. Assisted Auth 采用显式状态机

**Decision**
- 定义 assisted-auth 状态机：
  - `ready_to_open_login`
  - `waiting_for_human`
  - `session_captured`
  - `session_reuse_check`
  - `crawl_after_auth`
  - `completed`
  - `failed`

**Rationale**
- 登录态 / 验证码流程天然不是一次请求就能完成
- 前端必须清楚当前是系统动作还是人工动作
- 这也便于记录失败点和操作证据

**Alternatives considered**
- 用简单布尔状态 `requires_human = true/false`
  - 被拒绝：无法表达中间态，不利于前端控制和复盘

### 4. 结果模型统一标准化

**Decision**
- 引入统一 smoke run 结果：
  - `scenario_id`
  - `status`
  - `stage`
  - `robots`
  - `crawl_strategy`
  - `requires_human`
  - `dataset_saved`
  - `analysis_passed`
  - `report_passed`
  - `artifacts`
  - `notes`
  - `error`
- 统一状态：
  - `passed`
  - `failed`
  - `blocked_by_robots`
  - `manual_checkpoint_required`
  - `skipped`

**Rationale**
- 现有各接口返回结构差异很大
- 若没有统一结果模型，前端验收中心会很难设计，后续脚本和日志也无法复用

### 5. 持久化优先保存 run 元数据，不保存敏感会话内容

**Decision**
- 持久化 smoke runs 与 step results
- 原始 Cookie / 会话仍留在现有 cookie store
- smoke 结果只记录平台、状态、是否可复用等摘要，不复制敏感凭证

**Rationale**
- 既满足复盘与审计，又避免把凭证写进 run 历史
- 这也更符合后续安全审视

### 6. 前端独立页面，而不是塞进 Crawl/Settings

**Decision**
- 新增独立“验收中心 / Smoke Center”页面
- 页面至少包含：
  - `Local Smoke`
  - `Live Public Smoke`
  - `Live Assisted Smoke`
  - 结构化结果区

**Rationale**
- smoke 是跨采集、数据集、分析、报告的运营控制台
- 不应只是 Crawl 页的一组附属按钮
- 独立页面更符合产品扩展空间

## Risks / Trade-offs

- `[Assist auth 生命周期复杂]` → 使用显式状态机、轮询式 run 查询和人工继续按钮，先不引入 SSE/WebSocket
- `[crawl.py 已过大]` → 新增独立 `smoke` router 和服务层，不继续堆到现有 crawl router
- `[数据库模型有双 Base 风险]` → 新的 smoke 持久化模型必须统一挂到 canonical `api.core.database.Base`
- `[外站 smoke 容易 flaky]` → 默认 smoke 以 local 为主，live-public/live-assisted 作为分层场景并保留 `skipped` / `blocked_by_robots` / `manual_checkpoint_required`
- `[平台扩展过快导致流程发散]` → 采用 scenario registry + assisted-auth 平台描述，而非平台硬编码

## Migration Plan

1. 创建 OpenSpec 合约与实现前计划
2. 后端先落：
   - scenario registry
   - smoke runner
   - 统一 run/result schema
   - 非登录态 local/live-public smoke
3. 前端落：
   - Smoke Center 页面
   - 场景选择与结果展示
4. assisted-auth 首先以 `Bilibili` 打通
5. 再将 assisted-auth 平台能力泛化成注册式扩展

回滚策略：
- 若新 smoke 模块不稳定，可暂时移除前端入口并保留后端模块为实验性接口
- 不影响现有 crawl、analysis、reports 主链能力

## Open Questions

- assisted-auth 启动时，是否需要非 headless 浏览器与固定窗口标题，以便人工操作更顺畅
- Smoke run 历史是否在第一版就进入数据库，还是先以内存/文件落地做最小实现
- 第一版是否需要展示详细 step-level payload，还是只展示摘要与证据链接
- 自定义站点 assisted-auth 的平台描述是直接用表单输入，还是晚一点再做配置化管理
