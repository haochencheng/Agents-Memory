---
created_at: 2026-03-28
updated_at: 2026-04-07
doc_status: active
---

# Phase 4 — Ingest 结构化摄取流水线

## 设计目标

现有系统只能通过 `amem new` 手动创建错误记录，缺乏将已有文档（PR 描述、会议记录、架构决策）结构化写入记忆系统的路径。

本阶段添加 `amem ingest` 流水线：
1. 读取源文档（Markdown 任意格式）
2. 调用 LLM 提取结构化洞察（JSON 格式）
3. 自动更新相关 Wiki 页面（timeline + compiled_truth）
4. 追加写入 `memory/ingest_log.jsonl`

---

## 架构设计

```
Source Document (PR / 会议记录 / 决策 / 代码审查)
    │
    ▼
  _call_llm (provider 无关：anthropic | openai | ollama)
    │
    ▼
  JSON 提取：
    ├── summary            → 中文摘要
    ├── topics             → 匹配已有 wiki topics
    ├── timeline_entry     → 追加到 wiki 时间线
    └── compiled_truth_update → 可选：更新 wiki 第一个 topic 的 compiled_truth
    │
    ├─── wiki/<topic>.md  append_timeline_entry
    ├─── wiki/<topic>.md  update_compiled_truth（仅 topics[0]，如果提供）
    └─── memory/ingest_log.jsonl   追加写
```

---

## 支持的摄取类型

| 类型 | 用途 |
|------|------|
| `pr-review` | Pull Request 描述 / 代码审查 |
| `meeting` | 会议记录、站会摘要 |
| `decision` | 架构决策记录（ADR）|
| `code-review` | 代码审查反馈 |

---

## 数据结构

### LLM 输出格式（JSON）

```json
{
  "summary": "修复了认证失败问题...",
  "topics": ["auth", "backend"],
  "timeline_entry": "2026-04-07 [pr-review] 修复了 OAuth token 验证失败问题",
  "compiled_truth_update": "（可选）更新后的 compiled_truth Markdown"
}
```

- `topics` 必须是已有 wiki topics，否则忽略
- `timeline_entry` 单行，最大 120 字符
- `compiled_truth_update` 可选，只更新 `topics[0]` 对应的页面

### Ingest Log 格式（JSONL）

文件路径：`memory/ingest_log.jsonl`

```jsonl
{"timestamp":"2026-04-07T10:15:00Z","ingest_type":"pr-review","source_path":"/path/pr.md","project":"myproj","summary":"...","topics":["auth"],"provider":"anthropic","model":"claude-sonnet-4-5"}
```

- 格式：每行一个 JSON 对象（JSONL）
- 追加写，永不覆盖
- `timestamp` 使用 UTC ISO 8601 格式（`Z` 结尾）

---

## 公开 API

### `agents_memory/services/ingest.py`

| 函数 | 签名 | 作用 |
|------|--------|------|
| `build_ingest_prompt(ingest_type, source_path, content, project, known_topics)` | `-> tuple[str,str]` | 构建 (system, user) prompt |
| `ingest_document(ctx, source_path, ingest_type, project, provider, model, dry_run)` | `-> IngestResult` | 核心摄取逻辑 |
| `read_ingest_log(ctx)` | `-> list[dict]` | 读取所有日志条目（跳过损坏行）|
| `cmd_ingest(ctx, args)` | `-> int` | CLI 入口 |

### `IngestResult` 数据类

```python
@dataclass
class IngestResult:
    ingest_type: str
    source_path: str
    project: str
    summary: str
    topics_updated: list[str]
    timeline_entries_added: int
    log_entry: dict
    dry_run: bool
    error: str
```

---

## CLI 命令

```bash
amem ingest <file> --type <type> [--project <id>] [--dry-run] [--log]
  --type      pr-review | meeting | decision | code-review  （必须）
  --project   项目 ID（可选，写入 ingest_log）
  --provider  anthropic | openai | ollama（默认 AMEM_LLM_PROVIDER 环境变量）
  --model     LLM 模型名（默认从 provider 推断）
  --dry-run   预览模式，不写入任何文件
  --log       显示最近 20 条 ingest 日志（无需指定 file）
```

**示例：**

```bash
# Ingest PR 描述
amem ingest docs/pr-123.md --type pr-review --project synapse-network

# 预览会议摘要提取结果
amem ingest meeting-notes.md --type meeting --dry-run

# 查看摄取日志
amem ingest dummy --log
```

---

## MCP Tool

```python
@mcp.tool()
def memory_ingest(
    content: str,
    source_type: str,          # pr-review | meeting | decision | code-review
    source_ref: str = "",      # 可读引用，如 "PR #123"
    project: str = "",
    dry_run: bool = False,
) -> str: ...
```

工作流：
1. 将 `content` 写入临时文件
2. 调用 `ingest_document()`
3. 删除临时文件
4. 返回 JSON 摘要

---

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `AMEM_LLM_PROVIDER` | `anthropic` | LLM 提供商 |
| `AMEM_LLM_MODEL` | 按 provider 推断 | 模型名称 |
| `ANTHROPIC_API_KEY` | — | Anthropic 必须 |
| `OPENAI_API_KEY` | — | OpenAI 必须 |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama 地址 |

---

## 测试覆盖

文件：`tests/test_ingest_service.py`（33 个测试）

| 测试类 | 覆盖内容 |
|---------|----------|
| `TestParseLlmJson` | JSON 解析、Markdown fence 剥离、损坏 JSON |
| `TestBuildIngestPrompt` | 系统/用户 prompt 内容检验，长内容截断 |
| `TestBuildLogEntry` | 字段完整性、timestamp 格式、所有类型 |
| `TestIngestLog` | 追加写、读取、空日志、多条目、损坏行跳过 |
| `TestIngestDocument` | dry_run 不写文件、无效类型报错、文件不存在、wiki timeline 更新、日志写入、未知 topic 忽略、所有类型 |
| `TestCmdIngest` | 缺参数、缺 type、无效 type、dry-run、--log、--project |

---

## 状态

✅ 已实现并测试通过。291 个全局测试 OK。


The current system only reads error records manually created via `amem new`.
There is no path for ingesting existing documents (PR descriptions, meeting notes,
architecture decisions, code review comments) into the structured memory.

This phase adds a `amem ingest` pipeline that reads a source document, calls an LLM
to extract structured insights, and automatically updates wiki pages + ingest log.

## Design

```
Source Document (PR / meeting / decision / code-review)
    │
    ▼
  _call_llm (provider-agnostic: anthropic | openai | ollama)
    │
    ▼
  JSON extraction:
    ├── summary       → IngestResult.summary
    ├── topics        → matched against existing wiki topics
    ├── timeline_entry → appended to wiki pages (newest-first)
    └── compiled_truth_update → optional wiki page update
    │
    ├─── wiki/<topic>.md — append_timeline_entry
    ├─── wiki/<topic>.md — update_compiled_truth (first topic, if provided)
    └─── memory/ingest_log.jsonl — append log entry
```

## Ingest Types

| Type         | Use Case                                |
|--------------|------------------------------------------|
| `pr-review`  | Pull request description / review       |
| `meeting`    | Meeting notes or standup summary        |
| `decision`   | Architecture decision record (ADR)      |
| `code-review`| Code review feedback                    |

## Ingest Log Format

JSONL file at `memory/ingest_log.jsonl`. Each line is a JSON object:

```json
{
  "timestamp": "2026-03-28T09:15:00Z",
  "ingest_type": "pr-review",
  "source_path": "/path/to/pr.md",
  "project": "myproject",
  "summary": "修复了认证失败问题...",
  "topics": ["auth", "backend"],
  "provider": "anthropic",
  "model": "claude-sonnet-4-5"
}
```

## CLI Commands

```bash
amem ingest <file> --type pr-review [--project myproj] [--dry-run]
amem ingest <file> --type meeting
amem ingest <file> --type decision [--provider ollama] [--model qwen2.5:7b]
amem ingest dummy --log           # Show last 20 ingest log entries
```

## MCP Tool

```python
memory_ingest(content, source_type, source_ref="", project="", dry_run=False)
```

## Files Changed

- `agents_memory/services/ingest.py` — NEW: ingest pipeline
- `agents_memory/commands/ingest.py` — NEW: command registration
- `agents_memory/app.py` — registered ingest command
- `agents_memory/mcp_app.py` — added `memory_ingest` MCP tool
- `tests/test_ingest_service.py` — NEW: 33 tests covering all paths

## Bug Fixed

**BUG-002**: `list_wiki_topics(ctx)` was called with `AppContext` instead of `ctx.wiki_dir`.
Fixed: `list_wiki_topics(ctx.wiki_dir)`, `append_timeline_entry(ctx.wiki_dir, ...)`,
`update_compiled_truth(ctx.wiki_dir, ...)`.
See: `docs/bugfix/BUG-002.md`

## Status

✅ Implemented and tested. 276/276 tests green.
