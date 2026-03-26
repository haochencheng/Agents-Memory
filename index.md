# Agent Memory Index — Hot Tier

> 这是 Agent 每次启动时**必须加载**的唯一文件，严格控制在 400 tokens 以内。
> 其余所有内容通过 semantic search 或按需读取。

## 当前活跃规则总数

| 类别 | 数量 | 文件 |
|------|------|------|
| 错误模式 (errors) | 7 | `errors/` |
| 升级规则 (promoted) | 1 | `memory/rules.md` |

## 最近升级的规则（Top 3）

- **2026-03-26-synapse-002**: .github/instructions/python.instructions.md (Gotchas)

## 最高频错误类别（Top 3）

| Category | Count |
|----------|-------|
| `config-error` | 2 |
| `build-error` | 1 |
| `logic-error` | 1 |

## 检索指引

- 写代码前：查 `memory/rules.md` 匹配项目领域规则
- 代码出错后：`python3 scripts/memory.py search  <keyword>`
- 写 Finance 代码：额外加载 `memory/rules.md`（Finance 段）
- 做文档变更：检查 docs-drift 类别的错误记录

## 快速提交新错误

```
errors/YYYY-MM-DD-<project>-<sequence>.md
```

格式见 `schema/error-record.md`
