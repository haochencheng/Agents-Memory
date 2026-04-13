---
created_at: 2026-04-13
updated_at: 2026-04-13
doc_status: active
---

# BUG-008 Explicit Relative Markdown Links Were Not Normalized

## Summary

在 wiki onboarding / backfill 新增“正文显式引用 -> candidate links”后，`../architecture.md` 这类相对 Markdown 链接没有被规范化成稳定的 `source_path`，导致本应命中的 wiki 页面关系没有被建立。

## Symptom

- `tests.test_project_onboarding_service.test_ingest_project_wiki_sources_extracts_explicit_markdown_links` 失败
- `tests.test_wiki_backfill.test_backfill_extracts_explicit_markdown_links_from_existing_pages` 失败
- 页面正文里已经写了 `[Architecture](../architecture.md)`，但 frontmatter 里仍然没有 `links`

## Root Cause

`agents_memory/services/project_onboarding.py` 在解析显式 Markdown 引用时，直接拼接 `Path(current_parent) / target`，保留了 `..` 片段，最终得到的是 `docs/guides/../architecture.md`，无法与已知页面的规范化 `source_path=docs/architecture.md` 对齐。

## Fix

- 为显式引用解析补齐稳定的 posix path 规范化
- 在生成 candidate links 前统一消解 `.` / `..`
- 重新运行 onboarding / backfill 相关回归测试

## Prevention Rule

任何基于源码路径生成的稳定关系键，都不能直接依赖未规范化的 `Path.as_posix()` 结果；必须先消解 `.` / `..`，再和索引中的规范路径比较。
