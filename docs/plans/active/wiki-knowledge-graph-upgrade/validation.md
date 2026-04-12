---
created_at: 2026-04-12
updated_at: 2026-04-12
doc_status: active
---

# Validation

## Code

- `python3 -m py_compile agents_memory/services/project_onboarding.py agents_memory/services/search.py agents_memory/services/wiki_backfill.py agents_memory/services/wiki_knowledge.py agents_memory/web/api.py agents_memory/web/models.py scripts/backfill_wiki_metadata.py tests/test_project_onboarding_service.py tests/test_web_api.py tests/test_wiki_backfill.py tests/test_wiki_knowledge.py`
- `python3 -m unittest tests.test_project_onboarding_service tests.test_wiki_backfill tests.test_wiki_knowledge -v`
- `npm exec tsc --noEmit`

## Functional

- onboarding 导入的新 wiki 页面应写入 `project / source_path / doc_type / tags`
- 同项目相关文档应自动出现第一批 `links`
- `/api/search` 对 wiki/workflow 不再退化为纯 contains
- `/api/search` 应将 concept graph 信号并入统一 rerank，而不是只对 wiki 做轻量 boost
- `/api/wiki/graph` 应返回 typed concept nodes，而不是纯 page nodes
- `/wiki/graph` 默认视图应避免 200+ 节点标签重叠成不可读圆环
- `scripts/backfill_wiki_metadata.py --dry-run --json` 应能列出历史 wiki 的 metadata / links 修复计划
