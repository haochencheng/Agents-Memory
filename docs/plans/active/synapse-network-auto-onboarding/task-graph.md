---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# Task Graph

## Work Items

- [x] 建立 Synapse-Network 自动接入 plan bundle
- [x] 抽取项目知识源发现与批量 wiki 导入服务
- [x] 为 `enable/bootstrap` 增加 `--ingest-wiki` 与 `--wiki-limit`
- [x] 新增前端可调用的项目自动接入 API
- [x] 修正项目 / wiki 统计元数据，保证前端按项目展示
- [x] 更新 `/wiki/ingest` 页面交互与日志输出
- [x] 为服务层、API、前端补测试
- [x] 对 `Synapse-Network` 实跑自动接入并截图验证

## Exit Criteria

- [ ] 自动接入流程可在 CLI 与前端两端独立完成
- [ ] `Synapse-Network` 接入后在 dashboard / project detail / wiki ingest 页面可见
- [ ] `plan-check`、`docs-check`、相关 Python 单测、前端测试通过