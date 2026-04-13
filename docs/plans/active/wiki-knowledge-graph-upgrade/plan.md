---
created_at: 2026-04-12
updated_at: 2026-04-13
doc_status: active
---

# Plan

## Phase 1 — Stable Metadata

- 在 project onboarding 写入稳定 `project / tags / links / source_path / doc_type`
- API 与前端暴露 `doc_type`、关系信息和分页状态

## Phase 2 — Auto Links

- 基于同项目、共享标签、相邻目录域生成候选 links
- 在 ingest 时写入 frontmatter `links`

## Phase 3 — Hybrid Search

- 复用现有 error FTS + vector
- 为 wiki/workflow 增加 SQLite FTS
- 统一搜索时把 graph relation 作为 rerank boost

## Phase 4 — Concept Graph

- 将 graph 节点升级为 typed concept nodes
- 从页面正文抽取第一层 `entity / decision / module / error_pattern`
- 页面只保留为 node metadata / 阅读入口
- 图视图默认按已连接节点、关系类型和项目分层展示

## Phase 5 — Historical Backfill

- 为历史 wiki 页面补齐 `project / source_path / doc_type / tags / links`
- 优先复用 legacy frontmatter `sources:` 作为 `source_path` 线索

## Phase 6 — Multi-View Graph Explorer

- `/wiki/graph` 默认进入 `Schema` 视图，而不是直接显示全量图
- `Explore` 视图只渲染焦点节点的 `1-hop / 2-hop` 邻居
- `Table` 视图提供项目、类型、关系和搜索词过滤
- 保留 `?node=` 深链语义，并让它自动落到 `Explore`
