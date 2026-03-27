---
created_at: 2026-03-28
updated_at: 2026-03-28
doc_status: active
---

# Changelog

本文件记录对外可见的仓库变更。优先记录会影响安装、命令行为、开源协作入口、验证门禁或发布流程的更新。

## Unreleased

### Added

- GitHub 开源协作入口：issue templates、PR template、code of conduct、security、support、funding。
- GitHub Actions PR 基础门禁：安装、`py_compile`、单元测试、`docs-check`。
- 公开 release flow：`docs/release-checklist.md` 与本 changelog 联动。

### Changed

- `pyproject.toml` 构建后端切换为 `setuptools.build_meta`，使干净环境中的 `pip install .` 可用。
- `docs-check` 现在会验证 `.github/workflows/ci.yml` 和 `docs/release-checklist.md` 的关键语义，而不只检查文件存在。

## 0.1.0

### Added

- 初始的 Shared Engineering Brain CLI、MCP、planning、validation、docs 治理基础结构。