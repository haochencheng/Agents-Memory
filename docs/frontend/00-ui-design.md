---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# Agents-Memory 前端 Web UI 设计方案

## 一、背景与目标

Agents-Memory 目前只有 CLI（`amem`）和 MCP 工具两种访问入口。知识库内容（Wiki、错误记录、规则）只能通过命令行查询，对不熟悉命令行的团队成员不友好，且无法直观浏览 wiki 关系图或搜索历史。

**目标：** 提供一套轻量 Web UI，让开发者无需 CLI 即可：
- 浏览、搜索 Wiki 知识库
- 查看/筛选错误记录
- 执行 wiki-compile / ingest 操作
- 可视化知识图谱（wiki 交叉链接）

---

## 二、技术选型

### 推荐方案：双层架构

```
Browser (React + TailwindCSS)
        │
        ▼ HTTP JSON
FastAPI REST API  (Python，复用 agents_memory 服务层)
        │
        ▼
agents_memory/services/*   (现有业务逻辑，无需修改)
        │
   ┌────┴────┐
   │         │
memory/wiki  errors/
(Markdown)   (Markdown)
```

### 快速方案（MVP）：Streamlit

| 维度 | Streamlit | FastAPI + React |
|------|-----------|-----------------|
| 实现周期 | 1天 | 3-5天 |
| 依赖 | `streamlit` only | fastapi + react + tailwind |
| 交互能力 | 基础 | 完整（路由/状态管理）|
| 可嵌入 VS Code | ❌ | ✅ Simple Browser |
| 生产部署 | 简单 | Docker / systemd |

**建议路径：** 先用 Streamlit 验证 UX，再迁移到 React 版本。

---

## 三、页面设计

### 3.1 整体布局

```
┌─────────────────────────────────────────────────────────────┐
│  🧠 Agents-Memory          [搜索框...]         [设置] [刷新] │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                   │
│  导航栏  │              主内容区                            │
│          │                                                   │
│ ● 概览   │                                                   │
│ ● Wiki   │                                                   │
│ ● 错误   │                                                   │
│ ● 搜索   │                                                   │
│ ● Ingest │                                                   │
│ ● 规则   │                                                   │
│          │                                                   │
└──────────┴──────────────────────────────────────────────────┘
```

---

### 3.2 P1：概览页（Dashboard）

**路由：** `/`

```
┌─────────────── 概览 ───────────────────────────────────┐
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  Wiki    │  │  错误    │  │  已摄取  │  │  规则  │ │
│  │  32 页   │  │  0 条    │  │  0 条    │  │  活跃  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│                                                         │
│  ── Wiki 健康检查 ──────────────────────────────────── │
│  ✅ 32 个页面，35 个 orphan → [查看详情]               │
│                                                         │
│  ── 最近 Ingest 记录 ───────────────────────────────── │
│  （空）                                                 │
│                                                         │
│  ── 错误记录热点 ───────────────────────────────────── │
│  （按 category/project 的分布柱状图）                   │
└─────────────────────────────────────────────────────────┘
```

**数据源：**
- `memory_wiki_list()` → topic 数量
- `memory_get_index()` → 错误总数
- `memory_wiki_lint()` → 健康状态摘要
- `read_ingest_log()` → 最近 5 条

---

### 3.3 P1：Wiki 知识库页

**路由：** `/wiki`、`/wiki/:topic`

#### 列表视图 `/wiki`

```
┌─────────────── Wiki 知识库 ────────────────────────────┐
│  [搜索关键词...]  [筛选: 全部 ▼]  [新建 topic]         │
│                                                         │
│  synapse-architecture     更新: 2026-04-07  ●高置信    │
│  └─ Synapse 系统架构…                                   │
│                                                         │
│  synapse-billing          更新: 2026-04-07  ●中置信    │
│  └─ 计费/支付模块…                                      │
│                                                         │
│  synapse-discovery        更新: 2026-04-07  ●中置信    │
│  └─ 服务发现模块…                                       │
│  ...                             [1/4 页]  [下一页 >]  │
└─────────────────────────────────────────────────────────┘
```

#### 详情视图 `/wiki/:topic`

```
┌────────── synapse-architecture ────────────────────────┐
│  [← 返回]  confidence: medium  updated: 2026-04-07     │
│  [编辑 compiled_truth]  [wiki-compile ▶]  [复制链接]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ## Compiled Truth                                      │
│  （渲染后的 Markdown 内容）                              │
│  > Synapse 是 agent-first 结算层...                     │
│  • 已知 Pattern: ...                                    │
│                                                         │
├──────── 时间线 ──────────────────────────────────────── │
│  2026-04-07  [wiki-ingest] 从 ARCHITECTURE.md 导入      │
│  ...                                                    │
├──────── 链接关系 ────────────────────────────────────── │
│  出链 (0)   入链 (0)   [建立链接]                       │
└─────────────────────────────────────────────────────────┘
```

**数据源：** 直接读 `memory/wiki/<topic>.md`（frontmatter + body）

---

### 3.4 P1：全文搜索页

**路由：** `/search`

```
┌─────────────── 搜索 ───────────────────────────────────┐
│  [🔍 输入关键词... 回车搜索]                             │
│  模式: ● Hybrid  ○ FTS only  ○ Vector only  limit: 10  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  搜索 "JWT auth" → 1 条结果                             │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  TEST-001  synapse-network  type-error  high     │   │
│  │  JWT auth failure — token verification throws…  │   │
│  │  FTS: 1.00  Vector: —  Combined: 0.40           │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ── Wiki 搜索结果 ──                                     │
│  synapse-ops-local-environment  "...jwt..."             │
└─────────────────────────────────────────────────────────┘
```

**数据源：** `hybrid_search()` / `search_fts()` + `search_wiki()`  
支持同时展示错误记录和 wiki 搜索结果，分区显示。

---

### 3.5 P2：错误记录页

**路由：** `/errors`、`/errors/:id`

```
┌─────────────── 错误记录 ───────────────────────────────┐
│  [搜索...]  项目[全部▼]  类别[全部▼]  状态[active▼]    │
│                                                         │
│  ID              项目              类别     严重  状态   │
│  ────────────── ────────────────  ───────  ────  ───── │
│  （空）当前无活跃错误记录                                │
│                                                         │
│                              [+ 新增错误记录]            │
└─────────────────────────────────────────────────────────┘
```

#### 详情视图 `/errors/:id`

```
┌─── AME-001 type-error ─────────────────────────────────┐
│  project: synapse-network  severity: high  status: new │
│  date: 2026-04-07  domain: backend                     │
├─────────────────────────────────────────────────────────┤
│  ## 问题描述                                             │
│  （Markdown 渲染）                                       │
├─────────────────────────────────────────────────────────┤
│  [标记为已解决]  [提升为规则]  [wiki-compile 相关 topic] │
└─────────────────────────────────────────────────────────┘
```

---

### 3.6 P2：Ingest 操作页

**路由：** `/ingest`

```
┌─────────────── Ingest 摄取 ────────────────────────────┐
│                                                         │
│  拖放文件或输入文本内容：                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  [拖放 .md 文件，或粘贴 Markdown 文本]            │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  类型: [pr-review ▼]   项目: [synapse-network ▼]       │
│  LLM:  [ollama ▼] / [qwen2.5:7b ▼]                    │
│  ☐ Dry Run（预览不写入）                                │
│                                                         │
│  [▶ 开始 Ingest]                                        │
│                                                         │
│  ── 摄取日志 (最近 20 条) ─────────────────────────── │
│  2026-04-07  pr-review  BUG-DEPOSIT-01...  synapse     │
└─────────────────────────────────────────────────────────┘
```

---

### 3.7 P2：Wiki 图谱视图

**路由：** `/wiki/graph`

```
┌─────────────── Wiki 知识图谱 ──────────────────────────┐
│  [过滤: synapse-*]  [布局: Force ▼]  [缩放 +/-]        │
│                                                         │
│          ┌──────────────────────────┐                  │
│          │     (D3.js 力导向图)     │                  │
│          │                          │                  │
│          │  ● synapse-architecture  │                  │
│          │    ↔ synapse-billing     │                  │
│          │    ↔ synapse-discovery   │                  │
│          │  ● synapse-billing       │                  │
│          │    (孤立节点: 橙色标注)  │                  │
│          └──────────────────────────┘                  │
│                                                         │
│  点击节点 → 跳转 wiki 详情页                             │
└─────────────────────────────────────────────────────────┘
```

**技术：** D3.js force simulation，节点颜色：
- 绿色：有双向链接
- 橙色：孤立（orphan）
- 灰色：stale（>30天未 compile）

---

### 3.8 P2：规则页

**路由：** `/rules`

```
┌─────────────── 工程规则 ───────────────────────────────┐
│  memory/rules.md 规则一览                               │
│                                                         │
│  ## Python 规则                                         │
│  • 禁止在 service 层调用 AppContext 而非 ctx.wiki_dir   │
│  • ...                                                  │
│                                                         │
│  ## 前端规则                                            │
│  • ...                                                  │
│                                                         │
│  [编辑规则]  [推送到所有注册项目]                        │
└─────────────────────────────────────────────────────────┘
```

---

## 四、REST API 设计

在 `agents_memory/web/` 新增 FastAPI 应用：

### 端点清单

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/wiki` | 列出所有 topics（含 frontmatter 元数据）|
| `GET` | `/api/wiki/:topic` | 获取 wiki 页面（frontmatter + rendered HTML）|
| `PUT` | `/api/wiki/:topic` | 更新 wiki compiled_truth |
| `GET` | `/api/wiki/lint` | 执行 wiki-lint，返回 issues 列表 |
| `POST` | `/api/wiki/:topic/compile` | 触发 wiki-compile（异步）|
| `GET` | `/api/errors` | 列出错误记录（支持 `?status=&project=&limit=`）|
| `GET` | `/api/errors/:id` | 获取单条错误记录 |
| `GET` | `/api/search` | 全文搜索（`?q=&mode=hybrid&limit=10`）|
| `POST` | `/api/ingest` | 摄取文档（`{content, source_type, project, dry_run}`）|
| `GET` | `/api/ingest/log` | 查看摄取日志（最近 N 条）|
| `GET` | `/api/rules` | 获取 memory/rules.md 内容 |
| `GET` | `/api/stats` | 系统统计（topic 数、错误数、ingest 数）|

### 异步任务（wiki-compile）

```
POST /api/wiki/:topic/compile
→ 返回 task_id: "compile-auth-20260407"

GET /api/tasks/:task_id
→ {status: "running" | "done" | "failed", result: ...}
```

---

## 五、目录结构

```
agents_memory/
  web/
    __init__.py
    api.py          ← FastAPI app，端点实现
    models.py       ← Pydantic 请求/响应模型
    renderer.py     ← Markdown → HTML 转换（python-markdown）

frontend/
  src/
    pages/
      Dashboard.tsx
      WikiList.tsx
      WikiDetail.tsx
      WikiGraph.tsx   ← D3.js 图谱
      Search.tsx
      Errors.tsx
      Ingest.tsx
      Rules.tsx
    components/
      MarkdownRenderer.tsx
      WikiCard.tsx
      ErrorBadge.tsx
      SearchBar.tsx
    api/
      client.ts       ← fetch wrapper
  package.json        ← vite + react + tailwindcss + d3
  vite.config.ts
```

---

## 六、Streamlit MVP 方案（快速验证）

用约 300 行 Python 实现核心功能，无需前端构建：

```python
# agents_memory/ui/streamlit_app.py
import streamlit as st

st.set_page_config(page_title="Agents-Memory", layout="wide")

page = st.sidebar.radio("导航", ["概览", "Wiki", "搜索", "错误记录", "Ingest"])

if page == "Wiki":
    topics = list_wiki_topics(ctx.wiki_dir)
    selected = st.selectbox("选择 Topic", topics)
    content = read_wiki_page(ctx.wiki_dir, selected)
    st.markdown(content)

elif page == "搜索":
    query = st.text_input("搜索关键词")
    if query:
        results = hybrid_search(ctx, query, limit=10)
        for r in results:
            st.write(f"**{r['id']}** ({r['project']}) — score: {r['combined_score']:.2f}")
```

**启动：**
```bash
streamlit run agents_memory/ui/streamlit_app.py --server.port 8501
```

---

## 七、实施路线图

### 阶段 1：Streamlit MVP（1天）
- [ ] `agents_memory/ui/streamlit_app.py`
- [ ] 概览、Wiki 列表+详情、搜索 3 个页面
- [ ] `bash scripts/start.sh --ui` 一键启动

### 阶段 2：FastAPI REST API（2天）
- [ ] `agents_memory/web/api.py` 全部端点
- [ ] Pydantic 请求/响应模型
- [ ] 单元测试（`tests/test_web_api.py`）

### 阶段 3：React 前端（3天）
- [ ] Vite + React + TailwindCSS 基础架构
- [ ] Wiki 列表/详情页
- [ ] 全文搜索页（Hybrid 结果分组展示）
- [ ] Ingest 操作页

### 阶段 4：知识图谱（1天）
- [ ] D3.js 力导向图
- [ ] 孤立/stale 节点颜色标注

---

## 八、与现有系统的集成

### start.sh 集成

```bash
# 扩展 start.sh，支持 --ui 参数
bash scripts/start.sh --ui          # 启动 FastAPI + 前端 dev server
bash scripts/start.sh --ui-streamlit # 启动 Streamlit UI
```

端口规划：

| 服务 | 端口 |
|------|------|
| Qdrant | 6333 |
| Ollama | 11434 |
| FastAPI | 8000 |
| React Dev | 5173 |
| Streamlit | 8501 |

### MCP 工具继续工作

Web UI 是额外的访问层，**不替换 MCP 工具**。两者共享同一套 `agents_memory/services/` 业务逻辑：

```
VS Code Copilot  →  MCP Tools  ──┐
                                   ├── agents_memory/services/*
Browser          →  Web UI API  ──┘
```

---

## 九、是否需要前端的判断依据

| 场景 | 建议 |
|------|------|
| 团队 < 3 人，全部是开发者 | CLI 够用，Streamlit 可选 |
| 团队有非工程师（PM/设计）| **需要 Web UI** |
| Wiki 内容 > 50 个 topic | **需要图谱视图** |
| 需要在移动端查看 | **需要 Web UI** |
| 需要非命令行触发 wiki-compile | **需要 Web UI** |

**综合建议：** 当前 32 个 Synapse wiki topics，建议先实现 **Streamlit MVP**（1天），验证高频用途后再投入 React 完整版。
