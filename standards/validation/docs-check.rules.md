---
created_at: 2026-03-26
updated_at: 2026-03-27
doc_status: active
---

# Validation Rules

文档验证：

1. docs entrypoint 完整
2. 关键命令文档一致
3. deprecated 内容已删除或显式标记
4. 文档元数据完整：`created_at`、`updated_at`、`doc_status` 可解析且合法
5. 设计/规划类文档的实施状态需要与当前实现一致
6. `docs/ai-engineering-operating-system.md` 必须保持单一 canonical 结构，不允许重复 front matter、重复主标题或历史章节回流
7. `docs/architecture.md` 只记录 repo 级实现 ADR，不重复产品定位、顶层 workflow、状态机与实施状态矩阵
8. `docs/modular-architecture.md` 只记录代码目录结构、模块分层与插件扩展点，不重复 ADR 技术取舍

代码验证：

1. `py_compile` 通过
2. 核心 services 有单元测试
3. 关键 CLI 流程至少有 smoke test

同步验证：

1. 行为变更必须同时看到 code diff、docs diff、test diff 中至少两层联动
2. 代码变更影响实现状态时，必须同步更新对应文档的状态标识与最后修改时间