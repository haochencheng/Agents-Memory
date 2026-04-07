---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# 前端产品设计文档

## 一、产品定位

Agents-Memory 前端是一个**工程师向**管理控制台，服务两类场景：

| 场景 | 目标用户 | 核心需求 |
|------|----------|----------|
| 团队记忆 Dashboard | 研发团队 | 监控多项目记忆状态、规则健康、工作流进度、定期检查结果 |
| Wiki 知识层 | 研发团队 + Agent | 浏览/编辑/关联 wiki 知识页面，追踪知识质量，可视化交叉引用 |

**前后端分离**：React SPA（`:3000`）调用 FastAPI（`:10100`）REST API。

---

## 二、技术栈（延续 01-tech-stack.md 决策）

| 层 | 选型 |
|----|------|
| 前端框架 | Vite + React 18 + TypeScript |
| UI 组件库 | TailwindCSS + shadcn/ui（headless，风格可控）|
| 路由 | React Router v6 |
| 状态管理 | Zustand（轻量，无冗余 boilerplate）|
| 数据请求 | TanStack Query（缓存 + 自动 refetch）|
| 图谱可视化 | D3.js v7（力导向图）|
| 富文本展示 | `react-markdown` + `highlight.js`（Markdown 渲染）|
| 表格 | TanStack Table v8 |
| 图表 | Recharts（折线/柱状图，Recharts 与 React 18 兼容性最佳）|
| 定时任务触发 | 前端轮询 + `setInterval`；后端 APScheduler（新增）|

---

## 三、Block 1 — 团队记忆 Dashboard

### 3.1 页面地图

```
/                        → Overview（系统健康一览）
/projects                → Projects（注册项目列表）
/projects/:id            → Project Detail（单项目记忆详情）
/memory                  → Memory Records（error records / rules / promote 状态）
/workflow                → Workflow（bootstrap / start-task / validate / close-task 状态）
/checks                  → Checks（docs-check / profile-check / plan-check 结果）
/scheduler               → Scheduler（定时任务配置与历史）
```

---

### 3.2 Overview（/）

**定位**：系统健康一览，类似 Grafana 首页。

**数据来源**：`GET /api/stats`，`GET /api/wiki/lint`，`GET /api/checks/summary`（新增）

**区块布局**：

```
┌─────────────────────────────────────────────────────────────┐
│  STAT CARDS: Wiki页数 | 错误记录数 | 摄入次数 | 项目数      │
├──────────────┬──────────────────────────────────────────────┤
│  Lint 健康分  │  最近工作流（最近 5 条 workflow 操作）       │
│  (圆形进度)   │                                              │
├──────────────┼──────────────────────────────────────────────┤
│  最近 Checks │  定时任务下次执行时间                         │
│  状态矩阵     │  （Scheduler 状态卡片）                       │
└──────────────┴──────────────────────────────────────────────┘
```

---

### 3.3 Projects（/projects 和 /projects/:id）

**定位**：统一管理多项目，类比 Jira Projects 入口页。

**数据来源**：`GET /api/projects`（已存在），`GET /api/projects/:id/stats`（新增）

**ProjectList 展示字段**：
- 项目名称 + 描述
- wiki 页数、错误记录数、规则数
- 最近 ingest 时间
- 健康状态徽章（绿/黄/红）

**ProjectDetail（/projects/:id）展示内容**：
- 项目信息卡（name / description / profile 路径）
- Wiki 文章列表（该项目专属，按 `updated_at` 排序）
- 最近错误记录（前 10 条）
- 工作流状态时间线（bootstrap→start-task→validate→close-task）
- 关联 Docs-check 最近结果

---

### 3.4 Memory Records（/memory）

**定位**：团队知识沉淀记录，相当于错误银行+规则看板。

**数据来源**：
- `GET /api/errors`（错误记录列表）
- `GET /api/errors/:id`（单条详情）
- `GET /api/rules`（规则列表）

**设计要点**：
- 左侧 Tab：`错误记录` / `规则` / `Promote 日志`
- 错误记录表格支持按 `project`、`severity`、`status`（open/resolved）过滤
- 规则列表显示 scope / rule_id / 状态 / 最近触发
- Promote 日志：从 error 晋升为 rule 的变更历史

---

### 3.5 Workflow（/workflow）

**定位**：追踪各项目工作流阶段执行状态，类比 GitHub Actions Runs 列表。

**数据来源**：`GET /api/workflow`（新增），`GET /api/workflow/:project`（新增）

**展示内容**：

```
项目: synapse-network
┌────────────────────────────────────────────────────────────┐
│ bootstrap ✓  →  start-task ✓  →  validate ✓  →  close-task ⏳ │
└────────────────────────────────────────────────────────────┘
最近 10 次操作记录（命令 / 时间 / 退出码 / 耗时）
```

- 状态图：水平步骤条（Step Progress Bar）
- 每步可展开查看日志摘要

---

### 3.6 Checks（/checks）

**定位**：查看 docs-check / profile-check / plan-check 的执行结果。

**数据来源**：`GET /api/checks`（新增），`GET /api/checks/:project`（新增）

**展示内容**：

| 字段 | 说明 |
|------|------|
| project | 项目名 |
| check_type | docs / profile / plan |
| status | pass / warn / fail |
| issues | 问题列表（file + message） |
| run_at | 执行时间 |

- 顶部：三个 check 类型汇总徽章
- 展开：每类 check 的 issue 列表（类似 ESLint 输出）
- 支持过滤 by project / check_type / status

---

### 3.7 Scheduler（/scheduler）

**定位**：配置和监控定时任务，类比 GitHub Actions 定时 workflow。

**数据来源**：`GET /api/scheduler/tasks`（新增），`POST /api/scheduler/tasks`（新增），`DELETE /api/scheduler/tasks/:id`（新增）

**功能点**：
1. **任务列表**：name / cron_expr / last_run / next_run / status
2. **创建任务**：选择 check 类型（docs / profile / plan）+ 选择项目 + 设置 cron
3. **任务历史**：最近 20 次执行记录（时间 / 耗时 / 结果摘要）
4. **结果通知**：结果写回 `/api/checks`，前端 Dashboard 自动感知

**后端实现**：使用 `APScheduler`（`BackgroundScheduler`），状态持久化到 `memory/scheduler_tasks.json`

---

## 四、Block 2 — Wiki 知识层

### 4.1 页面地图

```
/wiki                    → Wiki Home（所有 wiki 话题列表）
/wiki/:topic             → Topic Detail（wiki 页面详情）
/wiki/:topic/edit        → Topic Edit（编辑 compiled_truth）
/wiki/graph              → Knowledge Graph（D3.js 交叉引用图）
/wiki/lint               → Lint Report（lint 问题汇总）
/wiki/ingest             → Ingest（摄入新知识）
```

---

### 4.2 Wiki Home（/wiki）

**定位**：Confluence Space 首页风格，所有知识话题一览。

**数据来源**：`GET /api/wiki`

**布局**：

```
┌─────────────────────────────────────────────────────────────┐
│ [搜索框] [Filter: project ▼] [Tag 过滤器]                   │
├─────────────────────────────────────────────────────────────┤
│  卡片网格（每卡片：topic / title / tags / word_count / 时间）│
│  ← 支持按 project 分组展示（Group By Project）               │
└─────────────────────────────────────────────────────────────┘
```

**搜索**：调用 `GET /api/search?q=...`（hybrid FTS+vector），结果高亮关键词

---

### 4.3 Topic Detail（/wiki/:topic）

**定位**：单页 Wiki 详情，类比 Confluence Page。

**数据来源**：`GET /api/wiki/:topic`，`GET /api/wiki/:topic/backlinks`（新增）

**三栏布局**：

```
┌─────────┬────────────────────────────┬─────────────────────┐
│ 目录    │ 正文（Markdown 渲染）       │ 元信息面板           │
│ (TOC)   │                            │ ─────────────────   │
│         │  ...                       │ Tags: [backend]      │
│         │  ## compiled_truth         │ 字数: 420            │
│         │  ┌───────────────┐         │ 最后更新: 2026-03-14 │
│         │  │ AI 合成事实    │         │ Backlinks: 3个       │
│         │  └───────────────┘         │ [编辑 compiled_truth]│
│         │                            │ [触发 Compile]       │
└─────────┴────────────────────────────┴─────────────────────┘
```

**功能点**：
- TOC 自动从 h2/h3 生成，锚点滚动
- `compiled_truth` 区块高亮展示（黄底边框，区别于普通内容）
- Backlinks 面板：哪些 wiki 页面引用了本页（`[[topic]]` 格式）
- `[触发 Compile]` 按钮：调用 `POST /api/wiki/:topic/compile`，轮询任务状态
- Compile 状态轮询：`GET /api/tasks/:task_id`，进度条显示

---

### 4.4 Topic Edit（/wiki/:topic/edit）

**定位**：编辑 `compiled_truth` 内容，类比 Confluence 页面编辑。

**数据来源**：`GET /api/wiki/:topic`（读取），`PUT /api/wiki/:topic`（写回）

**功能点**：
- 左右分栏：Markdown 编辑器（Monaco Editor / CodeMirror） + 实时预览
- 仅允许编辑 `compiled_truth` 字段（保护原始 raw 内容不被覆盖）
- 保存前 diff 提示（显示改动行数）
- 提交：调用 `PUT /api/wiki/:topic`，成功后跳转回 Detail 页

---

### 4.5 Knowledge Graph（/wiki/graph）

**定位**：D3.js 力导向图，可视化 wiki 话题间的交叉引用关系。

**数据来源**：`GET /api/wiki/graph`（新增）

**响应结构**：
```json
{
  "nodes": [
    {"id": "synapse-architecture", "title": "Synapse Architecture", "project": "synapse-network", "word_count": 420}
  ],
  "edges": [
    {"source": "synapse-architecture", "target": "token-design", "type": "wiki_link"}
  ]
}
```

**交互设计**：
- 节点颜色 = 所属项目（跨项目链接直观呈现）
- 节点大小 = word_count（知识密度）
- 悬停节点：展示 title + tags + word_count tooltip
- 点击节点：跳转到 `/wiki/:topic`
- 跨项目边用虚线表示
- 右上角：项目颜色图例 + "过滤到项目" 下拉

---

### 4.6 Lint Report（/wiki/lint）

**定位**：wiki 质量报告，类比 SonarQube Issues 页面。

**数据来源**：`GET /api/wiki/lint`

**布局**：
- 顶部：问题总数 / warning 数 / info 数 汇总卡片
- 问题列表：按 `topic` 分组，展示 line / level / message
- 支持按 `level`（warning / info）过滤
- 每条问题旁：`[去修复]` 快捷链接 → 跳转到 `/wiki/:topic/edit`

---

### 4.7 Ingest（/wiki/ingest）

**定位**：新知识摄入入口，类比 Confluence Import / Jira Bulk Import。

**数据来源**：`POST /api/ingest`，`GET /api/ingest/log`

**表单字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| project | select | 选择目标项目 |
| source_type | radio | file / url / text |
| content | textarea / file / url input | 待摄入内容 |
| tags | tag input | 关联标签 |
| dry_run | checkbox | 是否 dry-run 预览 |

**提交后**：实时显示摄入进度（pipeline 各阶段：解析→分块→向量化→写入）

**Ingest 日志**：下方展示最近 20 条摄入历史（`GET /api/ingest/log`）

---

## 五、路由设计

```
/                           Overview
/projects                   Projects List
/projects/:id               Project Detail
/memory                     Memory Records
/workflow                   Workflow
/checks                     Checks
/scheduler                  Scheduler
/wiki                       Wiki Home
/wiki/graph                 Knowledge Graph
/wiki/lint                  Lint Report
/wiki/ingest                Ingest
/wiki/:topic                Topic Detail
/wiki/:topic/edit           Topic Edit
```

**React Router v6 布局结构**：

```
<RootLayout>             ← 顶部导航 + 侧边栏
  <DashboardLayout>
    /                    → <Overview />
    /projects            → <ProjectList />
    /projects/:id        → <ProjectDetail />
    /memory              → <MemoryRecords />
    /workflow            → <Workflow />
    /checks              → <Checks />
    /scheduler           → <Scheduler />
  </DashboardLayout>
  <WikiLayout>
    /wiki                → <WikiHome />
    /wiki/graph          → <KnowledgeGraph />
    /wiki/lint           → <LintReport />
    /wiki/ingest         → <Ingest />
    /wiki/:topic         → <TopicDetail />
    /wiki/:topic/edit    → <TopicEdit />
  </WikiLayout>
</RootLayout>
```

---

## 六、导航结构

```
侧边栏:
─── Dashboard
    ├── Overview         (/)
    ├── Projects         (/projects)
    ├── Memory Records   (/memory)
    ├── Workflow         (/workflow)
    ├── Checks           (/checks)
    └── Scheduler        (/scheduler)
─── Wiki
    ├── All Topics       (/wiki)
    ├── Knowledge Graph  (/wiki/graph)
    ├── Lint Report      (/wiki/lint)
    └── Ingest           (/wiki/ingest)
```

---

## 七、组件库规划

| 组件 | 用途 | 位置 |
|------|------|------|
| `StatCard` | 数字统计卡片（带趋势箭头）| 首页 / Project Detail |
| `HealthBadge` | 绿/黄/红状态徽章 | Project List / Checks |
| `WorkflowStepper` | 水平步骤进度条 | Workflow 页 |
| `WikiCard` | Wiki 话题卡片 | Wiki Home |
| `TopicRenderer` | Markdown 渲染 + TOC + compiled_truth 高亮 | Topic Detail |
| `BacklinkPanel` | 反向链接列表 | Topic Detail |
| `KnowledgeGraph` | D3.js 力导向图 | /wiki/graph |
| `LintIssueList` | Lint 问题列表（分组+过滤）| Lint Report |
| `IngestForm` | 知识摄入表单 | /wiki/ingest |
| `SchedulerTaskTable` | 定时任务列表 + 操作 | Scheduler |
| `CompileProgress` | LLM Compile 进度轮询 | Topic Detail |
| `CheckResultMatrix` | checks 状态矩阵 | Overview / Checks |
| `FilterBar` | 通用多维过滤工具栏 | Memory / Checks / Wiki Home |

---

## 八、新增 API 需求（对比现有 03-api-contract.md）

以下端点需在 `agents_memory/web/api.py` 中新增：

### Dashboard Block

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/projects` | GET | 返回注册项目列表（已有服务，补端点）|
| `/api/projects/:id/stats` | GET | 单项目统计（wiki数/错误数/规则数/最近ingest）|
| `/api/workflow` | GET | 全部项目工作流状态列表 |
| `/api/workflow/:project` | GET | 单项目工作流状态 + 操作历史 |
| `/api/checks` | GET | 全部 check 结果列表（分页）|
| `/api/checks/:project` | GET | 单项目 check 结果 |
| `/api/checks/summary` | GET | 三类 check 汇总徽章数据 |
| `/api/scheduler/tasks` | GET | 定时任务列表 |
| `/api/scheduler/tasks` | POST | 创建定时任务 |
| `/api/scheduler/tasks/:id` | DELETE | 删除定时任务 |
| `/api/scheduler/tasks/:id/history` | GET | 任务执行历史 |

### Wiki Block

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/wiki/graph` | GET | 返回 nodes + edges（交叉引用图数据）|
| `/api/wiki/:topic/backlinks` | GET | 反向链接列表（谁引用了本 topic）|

---

## 九、前端项目目录结构

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── src/
│   ├── main.tsx               ← 入口
│   ├── App.tsx                ← Router 根
│   ├── api/                   ← TanStack Query hooks
│   │   ├── useStats.ts
│   │   ├── useProjects.ts
│   │   ├── useWiki.ts
│   │   ├── useChecks.ts
│   │   ├── useWorkflow.ts
│   │   └── useScheduler.ts
│   ├── components/            ← 共享组件
│   │   ├── StatCard.tsx
│   │   ├── HealthBadge.tsx
│   │   ├── WorkflowStepper.tsx
│   │   ├── WikiCard.tsx
│   │   ├── TopicRenderer.tsx
│   │   ├── BacklinkPanel.tsx
│   │   ├── KnowledgeGraph.tsx
│   │   ├── LintIssueList.tsx
│   │   ├── IngestForm.tsx
│   │   ├── SchedulerTaskTable.tsx
│   │   ├── CompileProgress.tsx
│   │   ├── CheckResultMatrix.tsx
│   │   └── FilterBar.tsx
│   ├── layouts/
│   │   ├── RootLayout.tsx
│   │   ├── DashboardLayout.tsx
│   │   └── WikiLayout.tsx
│   ├── pages/
│   │   ├── dashboard/
│   │   │   ├── Overview.tsx
│   │   │   ├── ProjectList.tsx
│   │   │   ├── ProjectDetail.tsx
│   │   │   ├── MemoryRecords.tsx
│   │   │   ├── Workflow.tsx
│   │   │   ├── Checks.tsx
│   │   │   └── Scheduler.tsx
│   │   └── wiki/
│   │       ├── WikiHome.tsx
│   │       ├── TopicDetail.tsx
│   │       ├── TopicEdit.tsx
│   │       ├── KnowledgeGraphPage.tsx
│   │       ├── LintReport.tsx
│   │       └── Ingest.tsx
│   ├── store/                 ← Zustand stores
│   │   ├── uiStore.ts         ← 全局 UI 状态（侧边栏折叠/主题）
│   │   └── filterStore.ts     ← 跨页过滤器状态
│   └── lib/
│       ├── api-client.ts      ← axios 实例（baseURL :10100）
│       └── utils.ts
```

---

## 十、开发优先级路线图

### Sprint 1 — 框架搭建（1 周）

| 任务 | 产出 |
|------|------|
| Vite + React 18 + TailwindCSS 初始化 | `frontend/` 目录 |
| React Router v6 路由骨架（全页面空壳）| App.tsx |
| RootLayout + DashboardLayout + WikiLayout | layouts/ |
| api-client.ts + TanStack Query 接入 | api/ hooks |
| CI：`npm run build` 验证通过 | GitHub Actions |

**验收**：所有路由可访问，无 console error，build 成功。

### Sprint 2 — Dashboard Block（2 周）

| 任务 | 产出 |
|------|------|
| Overview 页：StatCard + CheckResultMatrix + WorkflowStepper | Overview.tsx |
| Projects 页：ProjectList + ProjectDetail | ProjectList.tsx / Detail.tsx |
| Memory Records 页：ErrorTable + RulesTable + 过滤 | MemoryRecords.tsx |
| Workflow 页：StepProgress + 操作历史表 | Workflow.tsx |
| Checks 页：LintIssueList + 过滤 | Checks.tsx |
| Scheduler 页：SchedulerTaskTable + 创建表单 | Scheduler.tsx |
| 后端新增 API：projects / workflow / checks / scheduler | api.py |

**验收**：Dashboard 全部页面数据联通，Scheduler 可创建/删除任务。

### Sprint 3 — Wiki Block（2 周）

| 任务 | 产出 |
|------|------|
| Wiki Home：卡片网格 + 搜索 + 项目分组 | WikiHome.tsx |
| Topic Detail：TopicRenderer + TOC + compiled_truth + BacklinkPanel | TopicDetail.tsx |
| Topic Edit：Monaco Editor + diff 预览 | TopicEdit.tsx |
| Knowledge Graph：D3.js 力导向图 + 交互 | KnowledgeGraph.tsx |
| Lint Report：分组问题列表 + 快捷修复入口 | LintReport.tsx |
| Ingest 表单 + 摄入日志 | Ingest.tsx |
| 后端新增 API：wiki/graph + backlinks | api.py |

**验收**：Wiki 全部页面联通，Knowledge Graph 可渲染并交互，Ingest 成功写入。

### Sprint 4 — 收尾（0.5 周）

| 任务 | 产出 |
|------|------|
| 响应式布局适配（1280px ~ 1920px）| 全页面 |
| 暗色模式（TailwindCSS dark:）| 全局 |
| Storybook 组件文档（可选）| `frontend/.storybook/` |
| E2E 测试（Playwright，覆盖 Overview + Wiki Detail）| `tests/e2e/` |
| `docs/frontend/09-e2e-test.md` 测试策略 | docs/ |

---

## 十一、风险与约束

| 风险 | 缓解 |
|------|------|
| APScheduler 状态内存丢失（进程重启后）| 持久化到 `memory/scheduler_tasks.json` |
| D3.js 节点过多（>500 节点）性能下降 | 默认展示当前项目子图，全图按需加载 |
| wiki graph API 计算链接耗时 | 启动时缓存，文件变更时 invalidate |
| Monaco Editor 包体积大（~2MB）| 动态 import（code splitting），仅 Edit 页加载 |
| `/api/workflow` 数据来源不确定 | Phase 1 从 `memory/projects.md` + logs 目录解析，Phase 2 增加结构化写入 |
| 无认证（v1 局限）| 仅 localhost 开放，API 写操作带 `# WRITE` 注释，v2 再加 token 认证 |

---

## 附录：与现有文档关系

| 文档 | 与本文关系 |
|------|-----------|
| `01-tech-stack.md` | 本文沿用其技术决策，新增 shadcn/ui + APScheduler |
| `02-architecture.md` | 本文前端目录结构是其 SPA 层的细化 |
| `03-api-contract.md` | 本文 Section 8 列出新增 API，需追加到该文档 |
| `04-plans.md` | 本文 Sprint 路线图是其后续 Phase 6+ 的延伸 |
| `07-react-migration-decision.md` | 本文是迁移决策的具体落地方案 |
