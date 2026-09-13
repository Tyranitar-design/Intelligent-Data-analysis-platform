## Why

`D:\智能数据分析平台` 已经具备 URL 采集、智能采集、robots.txt 合规检查、数据集保存、Analysis、Reports 等主链能力，但当前缺少一个统一、可重复、可控的验收体系来验证这些能力是否真正协同工作。

随着后续数据分析、机器学习、深度学习、数据挖掘和可视化工作越来越依赖采集与上传数据，项目现在需要一个面向产品内操作的 Smoke Center，以合规方式覆盖本地数据、公开 URL 和人机协同登录态采集场景。

## What Changes

- 新增一个产品级 `Smoke Center / 验收中心`，用于在前端可控地运行主链 smoke 验收，而不是只依赖散落的脚本。
- 新增后端 `smoke` 编排层，复用现有 `crawl / auth / analysis / reports` 能力，统一场景定义、运行状态、执行结果和证据输出。
- 新增分层 smoke 场景模型，覆盖：
  - `local`：本地/上传数据主链验收
  - `live-public`：公开 URL + robots.txt 合规检查 + 静态/动态采集
  - `live-assisted`：登录态 / 验证码 / 人机协同采集
- 新增人机协同登录 smoke 流程，首个验证平台为 `Bilibili`，但架构必须支持后续扩展到其它需要登录态或验证码的网站。
- 将 `robots.txt` 合规检查、人工介入状态、数据集保存、Analysis、Reports 结果统一映射到结构化 smoke 结果模型。
- 新增实现前计划文档，用于后续按阶段执行而不直接跳进实现。

## Capabilities

### New Capabilities
- `smoke-center`: 产品内验收中心，支持本地 smoke、公开 URL smoke 和人机协同 smoke 的统一操作与结果展示
- `assisted-auth-collection`: 面向登录态 / 验证码场景的人机协同采集能力，支持登录打开、人工介入、会话捕获、会话复用和后续采集验证
- `smoke-run-orchestration`: 统一场景注册、执行编排、状态管理、结果归档和证据输出能力

### Modified Capabilities
- `harness-engineering`: 扩展到 smoke 编排、状态机、标准结果模型和验收证据输出的一致工程约束
- `vibe-coding`: 扩展到验收中心前端交互、人工检查点、操作员可读反馈和状态展示的一致交互规范

## Impact

- 后端新增独立 `smoke` 路由与服务模块，避免继续膨胀 `backend/api/routers/crawl.py`
- 前端新增独立“验收中心 / Smoke Center”页面、API 层和导航入口
- 需要新的 smoke 场景定义、运行状态模型、结果模型与持久化策略
- 需要复用并约束现有 `robots-check`、`url/crawl`、`smart/v2`、`auth/*`、`dataset save/list`、`analysis`、`reports` 等接口
- 需要明确人机协同登录的合规边界：不自动绕过验证码，只支持人工介入与会话复用验证
