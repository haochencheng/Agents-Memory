---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# Execution Plan

## Scope

- 影响模块：`agents_memory/services/integration_enable.py`、`agents_memory/services/workflows.py`、`agents_memory/web/api.py`
- 新增模块：项目知识自动摄取服务
- 影响前端：`frontend/src/pages/wiki/Ingest.tsx`、相关 API hooks 与 E2E 页面验证
- 影响文档：`docs/guides/integration.md`、`docs/guides/commands.md`、maintenance bug 记录

## Design Notes

- 复用现有 `enable/bootstrap` 作为项目纳管入口，避免引入新的分叉工作流
- 项目知识摄取以 Markdown 源发现 + wiki 导入为核心，不依赖 LLM 才能完成基础接入
- 通过 wiki frontmatter 的 `project` / `source_path` 建立项目视图与知识页的关联
- API 与前端复用同一套服务逻辑，避免 CLI / Web 行为漂移

## Change Set

- 代码改动：新增项目知识源发现与批量 wiki 导入；扩展 enable / bootstrap 参数；新增项目自动接入 API
- API 改动：返回 per-project wiki / ingest 统计；wiki topic 暴露 `project` 元数据
- 前端改动：`/wiki/ingest` 新增项目自动接入表单与结果日志；修复项目详情页参数读取
- 文档改动：补充一键接入与 Synapse-Network 示例说明
- 维护改动：记录接入可见性相关 bugfix

## Rollout Notes

- 先以 `Synapse-Network` 为例验证自动发现的知识源集合是否合理
- 若自动发现文件过多，则通过 `--wiki-limit` / API `max_files` 控制首轮导入规模
- 优先确保默认体验稳定，再考虑更细粒度的 include / exclude 配置