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
6. `README.md` 只作为开源仓库首页与文档入口，不展开完整教程正文
7. `docs/ai-engineering-operating-system.md` 必须保持单一 canonical 结构，不允许重复 front matter、重复主标题或历史章节回流
8. `docs/architecture.md` 只记录 repo 级实现 ADR，不重复产品定位、顶层 workflow、状态机与实施状态矩阵
9. `docs/modular-architecture.md` 只记录代码目录结构、模块分层与插件扩展点，不重复 ADR 技术取舍
10. `docs/integration.md` 只记录目标项目接入流程、验证和排错，不重复仓库内部模块分层设计
11. `docs/commands.md` 只记录命令总表、参数和分组参考，不重复目标项目接入步骤
12. `docs/getting-started.md` 只记录本仓库本地安装、启动与调试，不重复目标项目接入流程
13. `docs/ops.md` 只记录日常运维、日志、索引、Qdrant、备份与故障处理，不重复首次安装与目标项目接入流程

代码验证：

1. `py_compile` 通过
2. 核心 services 有单元测试
3. 关键 CLI 流程至少有 smoke test

同步验证：

1. 行为变更必须同时看到 code diff、docs diff、test diff 中至少两层联动
2. 代码变更影响实现状态时，必须同步更新对应文档的状态标识与最后修改时间