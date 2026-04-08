---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# Validation Route

## Required Checks

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile $(find agents_memory scripts -name '*.py' -print)
python3 scripts/memory.py plan-check .
python3 scripts/memory.py docs-check .
```

## Task-Specific Checks

- `python3 -m unittest discover -s tests -p 'test_integration_service.py' -v`
- `python3 -m unittest discover -s tests -p 'test_web_api.py' -v`
- `cd frontend && npm test -- --runInBand`
- `cd frontend && npx playwright test tests/e2e/pages/projects.spec.ts tests/e2e/pages/overview.spec.ts tests/e2e/pages/wiki-home.spec.ts`
- `python3 scripts/memory.py bootstrap /Users/cliff/workspace/agent/Synapse-Network --full --ingest-wiki`

## Execution Status

- 已通过：`test_project_onboarding_service.py`
- 已通过：`test_integration_service.py`
- 已通过：`test_web_api.py`
- 已通过：`test_wiki_service.py`
- 已通过：frontend Vitest unit tests
- 已通过：frontend build
- 已通过：`plan-check`、`docs-check`、`py_compile`
- 已通过：Playwright `onboarding-success.spec.ts`，已生成截图证据
- 已通过：真实 FastAPI `:10100` 健康检查与 `/api/onboarding/bootstrap` 联调
- 已通过：`Synapse-Network` 真实项目接入，返回 `ingested_files=24`，项目统计 `wiki_count=25`、`ingest_count=24`，`doctor` 状态为 `READY`
- 已通过：发现并修复 `amem mcp-setup` 无法修复旧 MCP 条目的问题，回归测试已补齐
- 已通过：发现并修复项目 wiki 自动发现会误纳入 `.pytest_cache/README.md` 且 runtime wiki/log 数据会污染 git 工作区的问题

## Evidence

- `/wiki/ingest` 接入页截图：`frontend/tests/e2e/screenshots/2026-04-08/onboarding-success-ingest-page.png`
- dashboard 截图：`frontend/tests/e2e/screenshots/2026-04-08/onboarding-success-overview.png`
- projects 列表截图：`frontend/tests/e2e/screenshots/2026-04-08/onboarding-success-projects.png`
- project detail 截图：`frontend/tests/e2e/screenshots/2026-04-08/onboarding-success-project-detail.png`
- 真实 API onboarding：`POST http://localhost:10100/api/onboarding/bootstrap`
- 真实项目统计：`GET http://localhost:10100/api/projects/synapse-network/stats`
- 真实 doctor：`python3.12 /Users/cliff/workspace/agent/Agents-Memory/scripts/memory.py doctor .`

## Review Notes

- 验证项目注册、profile / standards、bridge / MCP、wiki 导入、前端展示链路是否闭环
- 如发现前后端接入可见性 bug，必须先记录到 maintenance，再修复并重跑验证

## Synapse-Network Verification

- `http://localhost:10000/`：Overview 中应出现 `synapse-network`
- `http://localhost:10000/projects`：项目列表应出现 `synapse-network`
- `http://localhost:10000/projects/synapse-network`：应展示非零 wiki / ingest 数据
- `http://localhost:10000/wiki/ingest`：应可直接触发项目自动接入，且日志显示导入文件数与 wiki topic 列表