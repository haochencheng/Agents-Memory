---
created_at: 2026-03-26
updated_at: 2026-03-28
doc_status: active
---

# Contributing to Agents-Memory

## Scope

Agents-Memory 正在从共享错误记忆系统演进为面向 AI coding agents 的 Shared Engineering Brain。欢迎贡献：

1. Memory 能力：错误记录、规则升级、搜索、同步。
2. Standards 能力：工程规范、docs 规范、review checklist。
3. Planning 能力：spec-first、task graph、workflow 模板。
4. Validation 能力：`docs-check`、`profile-check`、`doctor`、相关测试。

## Working Agreement

提交行为变更时，请默认同步更新：

1. 代码
2. 文档
3. 测试或验证脚本

如果变更只停留在其中一层，仓库很快就会发生漂移。

## Collaboration Entry Points

为了让公开协作入口保持一致，请优先使用仓库内置模板：

1. 缺陷反馈使用 `.github/ISSUE_TEMPLATE/bug_report.md`。
2. 能力建议使用 `.github/ISSUE_TEMPLATE/feature_request.md`。
3. 提交 PR 前按 `PULL_REQUEST_TEMPLATE.md` 补齐摘要、验证结果、docs/tests 联动说明。
4. 社区互动与反馈边界遵循 `CODE_OF_CONDUCT.md`。

## Local Validation

提交前至少运行：

```bash
python3.12 -m unittest discover -s tests -p 'test_*.py'
python3.12 -m py_compile $(find agents_memory scripts -name '*.py' -print)
python3 scripts/memory.py docs-check .
```

如果你改了 profile、integration 或模板，建议再补跑：

```bash
python3 scripts/memory.py profile-check .
python3 scripts/memory.py doctor .
```

## Repository Boundaries

以下内容属于本地运行数据，不应进入公开仓库：

```text
index.md
memory/projects.md
memory/rules.md
errors/*.md
.vscode/mcp.json
logs/
vectors/
```

新增模板或文档时，请避免：

1. 写入 author-specific 绝对路径。
2. 假设只有 GitHub Copilot 一种 agent。
3. 把未来计划写成已经实现的能力。

## Design Direction

欢迎优先推进这些方向：

1. 让 `standards/` 和 `profiles/` 更可安装、更可验证。
2. 让 planning workflow 从文档变成真正的执行模板。
3. 让 validation 从人工约定变成机械门禁。
4. 保持 CLI dispatch、services、agent adapters 的模块边界清晰。
