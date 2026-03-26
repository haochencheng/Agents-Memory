# Agent Memory Index — Hot Tier

> Public example template. Your local runtime copy is generated as `index.md` on first run.
> Keep the local file small; this hot-tier summary should stay under 400 tokens.

## 当前活跃规则总数

| 类别 | 数量 | 文件 |
|------|------|------|
| 错误模式 (errors) | 0 | `errors/` |
| 升级规则 (promoted) | 0 | `memory/rules.md` |

## 最近升级的规则（Top 3）

_暂无_

## 最高频错误类别（Top 3）

| Category | Count |
|----------|-------|
| _暂无_ | - |

## 检索指引

- 写代码前：查 `memory/rules.md` 匹配项目领域规则
- 代码出错后：`python3 scripts/memory.py search <keyword>`
- 写 Finance 代码：额外加载 `memory/rules.md`（Finance 段）
- 做文档变更：检查 docs-drift 类别的错误记录

## 快速提交新错误

```text
errors/YYYY-MM-DD-<project>-<sequence>.md
```

格式见 `schema/error-record.md`