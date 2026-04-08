---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# Plan Bundle

## Task

Synapse-Network 自动化接入 Agents-Memory

## Outcome

- 以 `/Users/cliff/workspace/agent/Synapse-Network` 为实例完成一键接入路径设计与实现
- 接入流程覆盖项目注册、profile / standards 装配、MCP / bridge、项目文档知识摄取
- 接入结果可通过前端 `http://localhost:10000/`、项目页、`/wiki/ingest` 验证

## Scope

- CLI / service：扩展 `amem bootstrap` / `amem enable` 的自动化接入能力
- API：提供项目路径驱动的一键接入与 wiki 批量摄取接口
- Frontend：在 `/wiki/ingest` 暴露项目自动接入入口，并展示接入结果
- Validation：单测、API 测试、前端 E2E、Synapse-Network 实跑验证与截图

## Acceptance Criteria

- [ ] `Synapse-Network` 可通过单个命令或单个前端动作完成接入
- [ ] 接入后项目在 dashboard 与 project detail 中可见，且 wiki / ingest 统计正确
- [ ] 自动摄取至少覆盖项目 README、AGENTS、设计文档与 `docs/` 下 Markdown 文档
- [ ] `http://localhost:10000/wiki/ingest` 可触发项目自动接入 / 自动摄取
- [ ] docs / code / tests / maintenance 记录同步更新