# Promoted Rules — Memory Core

这里存放从错误记录升级（promoted）的规则。
每条规则都有源错误记录 ID 和已写入的 instruction 文件位置。

> **触发升级条件**：同类错误 repeat_count ≥ 2，或 severity=critical 的错误经复盘后。

---

## TypeScript / Frontend

### TS-001 `.filter()` 不是类型守卫
- **来源**：`2026-03-26-spec2flow-001`
- **规则**：需要收窄数组元素类型时，必须用 `(x): x is T` 谓词函数传给 `.filter()`，不能依赖运行时逻辑做 TypeScript 类型收窄。用 `as T` 断言哑火错误是技术债，根因未解决。
- **已写入**：待写入 Spec2Flow 的 instructions（当前暂存于此）

---

## Python / FastAPI

### PY-001 Pydantic 持久化兼容性
- **来源**：`2026-03-26-synapse-002`
- **规则**：持久化 Pydantic 模型时若未来可能改 alias，须在反序列化层加兼容适配，不能假设历史数据与当前 schema 格式永远一致。
- **已写入**：`.github/instructions/python.instructions.md` (Gotchas)

### PY-002 服务内共享 Postgres DSN
- **来源**：`2026-03-26-synapse-001`
- **规则**：同一服务内多个模块共享同一 Postgres 实例时，使用单一共享 DSN 字段，不要为每个模块单独声明 `*_POSTGRES_DSN`。
- **已写入**：`provider_service/.env.example`

---

## Finance / Backend

_暂无_

---

## Docs / Config

_暂无_
