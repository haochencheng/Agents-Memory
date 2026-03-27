---
created_at: 2026-03-28
updated_at: 2026-03-28
doc_status: active
---

# 发布检查清单

## 文档边界

本文件只记录版本发布前后需要执行的步骤。

- 对外变更内容记录在顶层 `CHANGELOG.md`。
- 仓库主页入口仍由 `README.md` 负责，不在这里重复完整教程。
- 日常开发命令仍以 `docs/commands.md` 为准，不在这里展开全量参数说明。

## 发布前

1. 更新 CHANGELOG.md，按 Added / Changed / Fixed 归类本次对外可见变更。
2. 确认 `pyproject.toml` 中的版本号与计划发布版本一致。
3. 本地或 CI 运行 `.github/workflows/ci.yml` 对应的基础校验全部通过。
4. 确认 README、CONTRIBUTING、开源协作入口、安装说明与当前实现一致。
5. 确认需要公开的 release notes 能从 CHANGELOG.md 中直接整理出来。

## 发布动作

1. 创建 Git tag，并使用与 `pyproject.toml` 一致的版本号命名。
2. 在 GitHub Release 中填写 release notes，优先基于 CHANGELOG.md 摘要生成。
3. 确认 Release 附带的源码归档可被外部用户正常获取。

## 发布后

1. 检查 GitHub Release 页面、tag、默认分支状态是否一致。
2. 检查 `.github/workflows/ci.yml` 在默认分支上的最近一次运行是否为绿色。
3. 为下一次迭代在 CHANGELOG.md 中保留 `## Unreleased` 区块。

## 使用规则

1. 发版流程变更时，必须同步更新 `CHANGELOG.md`、本文件和对应验证。
2. 如果某次改动影响安装、命令行为或开源协作面，应在合并时就补入 CHANGELOG，而不是等发版前集中回忆。