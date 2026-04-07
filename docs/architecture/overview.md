---
created_at: 2026-03-26
updated_at: 2026-04-07
doc_status: active
---

# Repo Architecture ADR

> 本文档只记录仓库级实现决策与技术取舍，不重复产品定位、顶层命令模型、状态机、实施状态矩阵。那些内容统一以 [AI Engineering Operating System](ai-engineering-operating-system.md) 为准。

---

## 边界说明

`docs/ai-engineering-operating-system.md` 负责：

1. 产品定位与系统目标。
2. Shared Engineering Brain 的能力模型。
3. 顶层 workflow、状态机、系统架构图。
4. 当前实施状态与 repo 级推进路线。

`docs/architecture.md` 只负责：

1. repo 级实现决策。
2. 关键技术取舍与后果。
3. 低层存储、检索、升级机制等 ADR。
4. 为什么采用某种实现路线，而不是目录树或模块分层清单本身。

`docs/modular-architecture.md` 负责：

1. 代码目录结构。
2. runtime / services / commands / integrations 的分层边界。
3. 插件层如何扩展，而不是为什么做某个技术取舍。

换句话说：

```text
AI Engineering Operating System = 产品与系统基线
architecture.md               = 仓库实现 ADR
```

---

## ADR-001: 三层分级记忆而非单文件

**日期**: 2026-03-26  
**状态**: Accepted

### 背景

单文件记忆方案（如一个大的 `memory.md`）随记录增长，每次 Agent 启动都需要全量加载，token 消耗线性增长。

### 决策

采用三层分级加载：

| 层级 | 文件 | 每次加载 | token 上限 |
|------|------|----------|------------|
| Hot  | `index.md` | 始终 | ≤ 400 |
| Warm | `memory/rules.md` | 按域按需 | ~1000 |
| Cold | `errors/*.md` | 检索命中时 | 按需单条 |

### 后果

- Agent 启动成本恒定（≤ 400 tokens），不随记录增长
- 检索延迟轻微增加（关键词搜索 < 50ms，向量搜索 < 200ms）
- 需要 CLI 维护 `index.md` 的统计摘要

---

## ADR-002: 关键词搜索 → LanceDB → Qdrant 渐进迁移

**日期**: 2026-03-26  
**状态**: Accepted

### 背景

不同规模阶段需要不同搜索后端：
- 初期（< 200 条）：关键词全文搜索，零依赖
- 中期（200-2000 条）：本地语义搜索，无需服务端
- 后期（2000+ 条 / 多 Agent）：共享向量数据库

### 决策

```
< 200 条    →  cmd_search()   Python 标准库，grep-style
≥ 200 条    →  cmd_vsearch()  LanceDB 本地向量库
多 Agent    →  cmd_to_qdrant() 迁移到 Qdrant Docker
```

自动策略切换：`cmd_stats()` 和 `cmd_update_index()` 在超过阈值时输出提示。

### 后果

- 迁移零成本：`errors/*.md` 文件格式不变，只替换搜索后端
- LanceDB 存储在 `vectors/`（gitignored），不污染代码库
- Qdrant 通过 `docker/docker-compose.yml` 启动，10 分钟可以上线

---

## ADR-003: 错误记录 → instruction Gotcha 的升级机制

**日期**: 2026-03-26  
**状态**: Accepted

### 背景

错误记录如果只存在 `errors/` 目录，下次 Agent session 不会自动加载，无法防止重复犯错。

### 决策

引入 `promote` 命令：当 `repeat_count ≥ 2` 或 `severity=critical` 时，将提炼规则 **显式写入** 对应的 `.github/instructions/*.instructions.md` 文件的 `Gotchas` 段。

写入后该规则随 instruction 文件自动生效，不再依赖每次检索记忆。

### 后果

- 高频错误 **永久固化** 为 Agent 行为约束
- instruction 文件成为"进化后状态"的权威载体
- 记忆系统是进化的工厂，instruction 是进化的结果

---

## ADR-004: 为什么不用 TurboQuant / 向量压缩

**日期**: 2026-03-26  
**状态**: Accepted

### 背景

Google TurboQuant（ICLR 2026）声称可以将向量压缩 6-8×。

### 结论

TurboQuant 解决的是 **LLM 推理时 KV Cache 的服务端压缩**（H100 GPU 级别），不是 App 层的 prompt token 消耗问题。它压缩的是模型内部的注意力键值向量，不能减少你发给 API 的输入 token 数量。

本项目的 token 问题通过 **分层架构 + 按需检索** 解决，与向量压缩算法无关。

---

## ADR-005: 为什么 embedding 用 OpenAI 而非本地模型

**日期**: 2026-03-26  
**状态**: Accepted

### 决策

使用 `text-embedding-3-small`（1536 维，$0.02/1M tokens）而非本地 BERT/ONNX 模型。

### 理由

| 维度 | OpenAI | 本地模型 |
|------|--------|----------|
| 安装复杂度 | `pip install openai` | torch + model download |
| 首次设置时间 | < 1 min | 5-30 min |
| 质量（中文+英文混合） | 优秀 | 一般 |
| 成本（200 条记录全量 embed） | < $0.01 | 0（但 CPU 时间） |
| 离线支持 | 否 | 是 |

本项目错误记录以中英文混合为主，OpenAI embedding 质量明显更好。向量库一旦建立，日常搜索无需再调用 API（只有 embed 命令需要）。

---

## 使用规则

后续新增内容时，遵守下面 3 条：

1. 如果是在说明产品能力、workflow、状态机或实施状态，写入 `docs/ai-engineering-operating-system.md`。
2. 如果是在解释某个 repo 级技术决策为什么这样做，写入 `docs/architecture.md`。
3. 如果一个段落同时在回答“产品要成为什么”和“代码为什么这样实现”，优先拆开，避免双向漂移。
