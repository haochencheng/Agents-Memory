---
created_at: 2026-03-26
updated_at: 2026-04-08
doc_status: active
---

# Planning Bundles

这个目录用于存放当前项目的 planning bundles。

## 目录结构

```
plans/
├── active/      ← 进行中 / 待执行的计划
├── archive/     ← 已完成的计划（只读归档）
└── deprecated/  ← 已废弃、不再执行的计划
```

### active/ 包含
- `bootstrap-checklist.md` — 项目初始化检查（PARTIAL）
- `refactor-watch.md` — 持续重构监控
- `onboarding-copilot-activation/` — Copilot 激活接入
- `refactor-agents-memory-*` — 各服务重构任务（进行中）

### active/ 评估（2026-04-08）
- 继续保留：`bootstrap-checklist.md`、`refactor-watch.md`
- 仍需执行：`onboarding-copilot-activation/`
- 仍需处理的 refactor bundle：
	- `refactor-agents-memory-mcp-app-py-memory-record-error/`
	- `refactor-agents-memory-services-integration-py-cmd-register/`
	- `refactor-agents-memory-services-integration-py-cmd-sync/`
	- `refactor-agents-memory-services-planning-py-init-refactor-bundle/`
	- `refactor-agents-memory-services-profiles-py-print-profile/`
- 已完成并迁出 active：`embed-ollama.md`、`planning-governance-gate/`、`refactor-agents-memory-services-integration-py-cmd-enable/`、`refactor-agents-memory-services-ingest-py-cmd-ingest/`
- 当前没有明确应迁入 `deprecated/` 的 active 项。

### archive/ 包含（已完成）
- `phase1-wiki-compiled-truth.md` ✅
- `phase2-hybrid-search.md` ✅
- `phase3-wiki-cross-references.md` ✅
- `phase4-ingest-pipeline.md` ✅
- `phase5-wiki-lint-mcp.md` ✅
- `embed-ollama.md` ✅
- `planning-governance-gate/` ✅
- `refactor-agents-memory-services-integration-py-cmd-enable/` ✅
- `refactor-agents-memory-services-ingest-py-cmd-ingest/` ✅
- `dogfood-close-task-workflow/` ✅
- `test-task/` ✅

### deprecated/ 包含（已废弃）
- 当前审查后暂无明确废弃项。
- 只有“明确被替代且不再需要执行”的计划才应移入此目录。

## 推荐流程

1. 运行 `amem plan-init "<task-name>" .`
2. 明确 runtime、tooling、docs、validation 的变更边界
3. 在交付前运行 `amem plan-check .`
4. 完成后将计划目录移入 `archive/`
5. 若确认目标已失效或被替代，则移入 `deprecated/`
