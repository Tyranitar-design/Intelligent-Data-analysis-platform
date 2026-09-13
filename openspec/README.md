# OpenSpec 智能数据分析平台规范

> 基于 OpenSpec 规范系统的项目管理文档

## 目录结构

```
openspec/
├── README.md           # 本文件
├── changes/            # 当前活跃变更（必须通过当前 OpenSpec 校验）
│   ├── index.md
│   └── baseline-and-architecture-phase1/
├── legacy/             # 历史提案与旧格式文档
└── specs/              # 规范参考
    ├── harness-engineering/   # Harness Engineering 规范
    └── vibe-coding/          # Vibe Coding 规范
```

## 规范层级

### Level 1: 基础规范
- [Harness Engineering](./specs/harness-engineering/) - 工程化实践规范
- [Vibe Coding](./specs/vibe-coding/) - 代码风格与协作规范

### Level 2: 项目规范
- 当前以 `docs/DEVELOPMENT_BASELINE.md`、`README-v2.md`、`openspec/specs/` 为主要基线参考

### Level 3: 变更提案
- 所有功能变更、重构、新特性都通过 `changes/` 目录管理
- 活跃变更必须使用当前 OpenSpec delta 格式
- 历史提案放入 `legacy/`，仅作参考

## 变更生命周期

```
Draft → In Review → Approved → Implemented → Merged
                    ↓
               Rejected
```

## 快速开始

1. **查看现有活跃变更**: 阅读 `changes/` 目录
2. **创建新变更**: 运行 `openspec new change <change-name>`
3. **查看规范**: 阅读 `specs/` 与 `docs/DEVELOPMENT_BASELINE.md`
4. **查看历史资料**: 参考 `legacy/`

## 相关资源

- [项目根目录](../)
- [后端代码](../backend/)
- [前端代码](../frontend/)
- [文档](../docs/)
- [开发基线](../docs/DEVELOPMENT_BASELINE.md)

---

*Last updated: 2026-05-09*
