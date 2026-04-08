---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# Validation Route

## Required Checks

```bash
/Users/cliff/workspace/agent/.venv/bin/python -m unittest tests.test_web_api
cd frontend && yarn vitest run src/test/ProjectDetail.test.tsx --reporter=dot
/Users/cliff/workspace/agent/.venv/bin/python scripts/memory.py plan-check .
/Users/cliff/workspace/agent/.venv/bin/python scripts/memory.py docs-check .
```

## Task-Specific Checks

- `curl http://127.0.0.1:10100/api/projects/synapse-network/wiki-nav`
- 打开 `http://localhost:10000/projects/synapse-network`
- 截图验证默认树形导航与视图切换结果

## Execution Status

- 已通过：`/Users/cliff/workspace/agent/.venv/bin/python -m unittest tests.test_web_api`
- 已通过：`cd frontend && yarn vitest run src/test/ProjectDetail.test.tsx --reporter=dot`
- 已通过：`/Users/cliff/workspace/agent/.venv/bin/python scripts/memory.py plan-check .`
- 已通过：`/Users/cliff/workspace/agent/.venv/bin/python scripts/memory.py docs-check .`
- 已通过：真实接口 `GET /api/projects/synapse-network/wiki-nav`，返回 `total_topics=127`
- 已通过：真实页面截图验证，默认 `Tree` 视图与切换后的 `Domain` 视图均可用
- 已通过：实现中发现并修复 `FE-006`，`docs/<file>.md` 不再被错误分入 `Readme.Md / Agents.Md` 之类脏分组

## Evidence

- project detail `Tree` 截图：`frontend/tests/e2e/screenshots/2026-04-08/project-detail-wiki-tree-live.png`
- project detail `Domain` 截图：`frontend/tests/e2e/screenshots/2026-04-08/project-detail-wiki-domain-live.png`
- 单项目导航接口：`GET /api/projects/synapse-network/wiki-nav`
- bugfix 记录：`docs/maintenance/frontend/FE-005-project-detail-flat-wiki-list-does-not-scale.md`
- bugfix 记录：`docs/maintenance/frontend/FE-006-project-wiki-domain-grouping-misclassified-docs-root-files.md`

## Review Notes

- 核对树形结构是否尊重 `source_path`
- 核对 `Domain` 分组是否可读且不丢失真实来源
- 已确认 `Tree` 视图首屏直接展示 `docs` 根与下级目录，适合 100+ 文档项目浏览
- 已确认 `Domain` 视图中存在 `Architecture`、`Architecture / Workflows`、`Docs Root`、`Ops` 等可读分组
- 如在实现过程中发现前端可用性 bug，需记录到 `docs/maintenance/frontend/`