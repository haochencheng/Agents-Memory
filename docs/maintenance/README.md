---
created_at: 2026-04-07
updated_at: 2026-04-08
doc_status: active
---

# 维护记录

本目录存放 Bug 修复和重构记录，追踪每次已知问题的根因与修复方案。

## Bug 修复记录

- [BUG-001](BUG-001.md)
- [BUG-002](BUG-002.md)
- [BUG-003](BUG-003.md)：wiki-lint `--check=value` 等号格式解析 Bug
- [BUG-004](BUG-004.md)：ingest 日志仍使用 `datetime.utcnow()`
- [BUG-005](BUG-005.md)：plans 根目录分组创建后未补齐 planning bundle 必需文件
- [BUG-006](BUG-006.md)：项目接入后 project API 仍返回全局 wiki 统计，导致接入可见性失真
- [BUG-007](BUG-007.md)：`amem mcp-setup` 遇到已有旧 agents-memory 条目时不会修复，导致 doctor 持续告警
- [BUG-008](BUG-008.md)：真实项目 onboarding 会把 `.pytest_cache` 文档当知识源并把本地 wiki/log 运行数据暴露到 git 工作区
- [REFACTOR-001](REFACTOR-001-complexity-watch-remaining.md)：复杂度 refactor-watch 遗留项


## 前端 Bug 记录

- [FE-001](frontend/FE-001-h1-toc-id-attribute-assertion.md)
- [FE-002](frontend/FE-002-datetime-utcnow-deprecated.md)
- [FE-003](frontend/FE-003-project-detail-route-param-mismatch.md)
- [FE-004](frontend/FE-004-vitest-includes-playwright-specs.md)

## 命名规范

- `BUG-NNN.md`：后端 / 服务层 Bug
- `REFACTOR-NNN.md`：重构追踪记录
- `frontend/FE-NNN.md`：前端 Bug
