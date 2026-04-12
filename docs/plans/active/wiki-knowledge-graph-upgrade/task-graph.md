---
created_at: 2026-04-12
updated_at: 2026-04-12
doc_status: active
---

# Task Graph

## Tasks

- [x] 改造 wiki 列表分页与详情页关系展示
- [x] 接入关系图推断边与可读性更高的图页面
- [x] onboarding 写入稳定 metadata 与候选 links
- [x] wiki/workflow 接入 FTS 搜索
- [x] 将 graph API 从 page node 过渡到 typed concept node
- [x] 从页面正文提取第一层 concept nodes（标题 / headings / tags / inline identifiers）
- [x] 提供历史 wiki metadata / links backfill 脚本与 dry-run 验证
- [x] 把 concept graph 信号进一步收敛进统一搜索排序

## Notes

- 当前 concept 抽取先走 deterministic 规则，不阻塞后续 LLM/entity extractor
- 历史 wiki backfill 已支持读取 legacy `sources:` 并推断 `source_path`
