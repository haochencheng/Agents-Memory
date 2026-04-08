---
created_at: 2026-04-07
updated_at: 2026-04-08
doc_status: active
---

# Execution Plan

## Scope

- 影响模块：`agents_memory/services/ingest.py`
- 影响命令：`amem ingest`
- 影响文档：`docs/plans/README.md`、`docs/maintenance/BUG-004.md`

## Design Notes

- 关键设计决策：保持 CLI 行为不变，仅拆分校验与执行路径
- 模块边界：`cmd_ingest` 仅负责调度，业务仍由 `ingest_document` 执行
- 兼容性风险：低；保留原参数格式和错误输出

## Change Set

- 代码改动：抽取 `_validate_ingest_options` 与 `_execute_ingest`，并将 ingest 日志时间改为 timezone-aware UTC
- 文档改动：记录 `BUG-004` 与计划分类调整
- 测试改动：新增 helper 级单元测试，保留原有 `cmd_ingest` 行为测试

## Refactor Execution
- Target hotspot: `agents_memory/services/ingest.py::cmd_ingest`
- Split branches/state transitions before adding new behavior.
- Preserve behavior with focused tests or validation commands before and after extraction.
- Re-run `amem doctor .` after the refactor and confirm the hotspot disappears or shrinks.
