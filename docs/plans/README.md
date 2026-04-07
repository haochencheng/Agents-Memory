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
├── active/    ← 进行中 / 待执行的计划
└── archive/   ← 已完成的计划（只读归档）
```

### active/ 包含
- `bootstrap-checklist.md` — 项目初始化检查（PARTIAL）
- `embed-ollama.md` — Ollama 嵌入功能
- `refactor-watch.md` — 持续重构监控
- `onboarding-copilot-activation/` — Copilot 激活接入
- `planning-governance-gate/` — 计划治理门控
- `refactor-agents-memory-*` — 各服务重构任务（进行中）

### archive/ 包含（已完成）
- `phase1-wiki-compiled-truth.md` ✅
- `phase2-hybrid-search.md` ✅
- `phase3-wiki-cross-references.md` ✅
- `phase4-ingest-pipeline.md` ✅
- `phase5-wiki-lint-mcp.md` ✅
- `dogfood-close-task-workflow/` ✅
- `test-task/` ✅

## 推荐流程

1. 运行 `amem plan-init "<task-name>" .`
2. 明确 runtime、tooling、docs、validation 的变更边界
3. 在交付前运行 `amem plan-check .`
4. 完成后将计划目录移入 `archive/`
