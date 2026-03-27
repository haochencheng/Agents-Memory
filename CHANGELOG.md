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

- GitHub Actions CI 现在拆分为独立的 `tests` 和 `docs` jobs，便于 branch protection 分别要求通过。
- `pyproject.toml` 构建后端切换为 `setuptools.build_meta`，使干净环境中的 `pip install .` 可用。
- `docs-check` 现在会验证 `.github/workflows/ci.yml` 和 `docs/release-checklist.md` 的关键语义，而不只检查文件存在。
- README 首页现在把 badge 与真实的 CI、releases、changelog、release checklist 工件直接联动，并显式展示 trust signals、质量门禁与发布纪律。
- README 中英文内容现在按语言整段分区，默认展开中文、折叠英文，降低双语交错阅读的噪音并提升整体切换体验。
- README 双语区块现在改为英文在上、中文在下，并同步调整顶部语言入口顺序，降低首次进入时的版面跳跃感。
- README 双语区块已去掉 `details` 折叠样式，改成连续展开排版，减少额外交互并提升首页直读性。
- README 首页现在把中英文重复的开场说明收敛到共享 hero 区，语言区块直接进入正文，整体更接近产品落地页而不是双份文档。
- README 进一步收敛为共享双语落地页：公共价值主张、workflow、trust signals、quick start 和文档入口集中展示，语言区块缩成摘要而不再重复整套正文。
- README 首页进一步强化转化路径：Quick Start 前移到 trust signals 之前，文档入口收敛为 4 个最高优先入口并指向 docs/README.md，总览区新增三栏卖点布局。

## 0.1.0

### Added

- 初始的 Shared Engineering Brain CLI、MCP、planning、validation、docs 治理基础结构。