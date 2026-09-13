# Proposal: 阶段一规范与基线收敛

## 概述

建立一个稳定、可协作、可验证的项目基线，为后续功能完善和架构收敛创造干净跑道。

## 现状分析

### 已有能力
- 项目已经形成后端、前端、OpenSpec、Docker、爬虫、分析、ML/DL 等完整骨架
- 已经存在 v2 风格后端入口、前端主线和企业化 Docker 草案
- 已经接入 Codex、OpenSpec、项目记忆和专家路由能力

### 问题识别
- `.gitignore` 过于薄弱，无法隔离本地运行产物和敏感文件
- 多个旧 OpenSpec change 不符合当前 delta 格式，导致校验失败
- 当前缺少一份明确的“什么应该入库、什么只留本地”的基线文档
- 存在新旧入口并存，但 canonical baseline 还没有被明确记录

## 目标

- 修复仓库基线与忽略策略
- 恢复 OpenSpec 活跃 change 的可校验状态
- 明确当前阶段的 canonical 开发入口
- 保留旧资料，但不让旧资料阻塞当前规范流程

## 实现方案

### 仓库基线
- 扩充 `.gitignore`
- 明确 versioned assets 与 local-only assets
- 保留 `.codex/`、`openspec/`、`AGENTS.md` 等协作资产

### OpenSpec 基线
- 新建一个合规的 phase-1 active change
- 将旧版、不合规、历史性的 change 文档迁移到 `openspec/legacy/`
- 更新 OpenSpec 说明文档与 change 索引

### 开发基线
- 记录当前推荐入口：
  - 后端：`backend/api/main.py`
  - 前端：`frontend/package.json`
  - Docker：`docker-compose-v2.yml`
- 将其写入开发基线文档，供后续阶段统一对齐

## 影响范围

| 类型 | 路径 | 说明 |
|------|------|------|
| 修改 | `.gitignore` | 修复忽略规则 |
| 新增 | `docs/DEVELOPMENT_BASELINE.md` | 记录阶段一基线 |
| 新增 | `openspec/changes/baseline-and-architecture-phase1/` | 新版合规 change |
| 修改 | `openspec/README.md` | 更新当前 OpenSpec 工作方式 |
| 修改 | `openspec/changes/index.md` | 更新活跃变更索引 |
| 新增 | `openspec/legacy/` | 保留旧版 change 文档 |

## 风险评估

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| 旧 OpenSpec 链接失效 | 低 | 在 `legacy/README.md` 中记录迁移去向 |
| 忽略规则过宽误伤版本化资产 | 中 | 仅忽略明确的本地产物、数据库、模型和缓存 |

## 时间估算

- 阶段 1A: 仓库忽略规则与基线文档
- 阶段 1B: OpenSpec 活跃 change 修复
- 阶段 1C: 旧变更迁移与校验

**总计**: 半天内可完成第一版稳定基线
