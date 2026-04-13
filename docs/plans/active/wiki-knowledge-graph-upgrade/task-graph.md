---
created_at: 2026-04-12
updated_at: 2026-04-13
doc_status: active
---

# Task Graph

## Tasks

- [x] 改造 wiki 列表分页与详情页关系展示
- [x] 接入关系图推断边与可读性更高的图页面
- [x] onboarding 写入稳定 metadata 与候选 links
- [x] onboarding / backfill 解析正文显式 Markdown 引用并补成 links
- [x] wiki/workflow 接入 FTS 搜索
- [x] wiki/workflow 接入 semantic vector scoring，并合并成 hybrid search
- [x] 将 graph API 从 page node 过渡到 typed concept node
- [x] 从页面正文提取第一层 concept nodes（标题 / headings / tags / inline identifiers）
- [x] 提供历史 wiki metadata / links backfill 脚本与 dry-run 验证
- [x] 把 concept graph 信号进一步收敛进统一搜索排序
- [x] 将 `/wiki/graph` 重构为 `Schema / Explore / Table` 多视图
- [x] 为图谱页补项目、类型、关系、搜索词过滤
- [x] 保留 `?node=` 深链语义，并让它默认进入 `Explore`
- [x] 为多视图图谱页补前端自动化测试

## Notes

- 当前 concept 抽取先走 deterministic 规则，不阻塞后续 LLM/entity extractor
- 历史 wiki backfill 已支持读取 legacy `sources:` 并推断 `source_path`
- 当前 semantic vector 先用本地 deterministic sparse vector 保持零外部依赖；后续可接真实 embedding provider 替换
- 当前前端交互先验证浏览模型，后续如节点规模继续增长，再评估切换到 G6 / Graphin / Cytoscape
