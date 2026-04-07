---
created_at: 2026-04-08
updated_at: 2026-04-08
doc_status: active
---

# Frontend E2E 自动化测试方案

## 一、目标

对 Agents-Memory 前端（`http://localhost:10000`）所有页面执行端到端自动化测试，验证：
1. 页面正常加载（无崩溃/空白/编译错误）
2. 关键 UI 元素可见（标题、导航、核心组件）
3. API 数据联通（有数据时正确展示，无数据时显示空状态占位）
4. 页面交互功能正常（表单提交、Tab 切换、导航跳转）

## 二、技术方案

| 工具 | 版本 | 用途 |
|------|------|------|
| Playwright | `@playwright/test` latest | 页面自动化 + 截图 |
| 浏览器 | Chromium (headless) | 跨平台一致性 |
| 截图目录 | `frontend/tests/e2e/screenshots/` | 每次测试截图存档 |
| BugFix 记录 | `docs/test/frontend/bugfix/` | 发现的 bug 记录 |

## 三、测试覆盖范围

### Dashboard Block

| 页面 | 路由 | 验证点 |
|------|------|--------|
| Overview | `/` | StatCards 可见、页面标题、无 ErrorAlert |
| Projects | `/projects` | 项目列表或空状态、page-title 可见 |
| Project Detail | `/projects/:id` | 回退按钮、标题、stats 卡片 |
| Memory Records | `/memory` | Tab 切换（错误记录/规则）、内容区域可见 |
| Workflow | `/workflow` | WorkflowStepper 可见或空状态 |
| Checks | `/checks` | Check 类型 Tab、状态汇总、结果列表 |
| Scheduler | `/scheduler` | 任务列表或空状态、新增按钮可见 |

### Wiki Block

| 页面 | 路由 | 验证点 |
|------|------|--------|
| Wiki Home | `/wiki` | 搜索框可见、话题列表或空状态 |
| Knowledge Graph | `/wiki/graph` | 画布元素可见 |
| Lint Report | `/wiki/lint` | 汇总卡片可见、issues 列表或空状态 |
| Ingest | `/wiki/ingest` | 表单元素可见、提交按钮 |

## 四、截图策略

每个测试页面生成两张截图：
1. `{page-name}-full.png` — 全页截图
2. `{page-name}-viewport.png` — viewport 截图（首屏）

截图存放路径：`frontend/tests/e2e/screenshots/{timestamp}/`

## 五、Bug 记录规范

发现 bug 时，在 `docs/test/frontend/bugfix/` 目录创建记录文件：

```
bugfix/
└── {YYYYMMDD}-{bug-id}-{简述}.md
```

Bug 记录格式见 `docs/test/frontend/bugfix/README.md`。

## 六、执行流程

```bash
# 1. 确保后端运行（:10100）
bash scripts/web-start.sh restart

# 2. 启动前端 dev server（:10000）
cd frontend && node_modules/.bin/vite --port 10000 &

# 3. 安装 Playwright
cd frontend && npm install --save-dev @playwright/test
npx playwright install chromium

# 4. 执行 E2E 测试
npx playwright test tests/e2e/ --reporter=html

# 5. 查看报告
npx playwright show-report
```

## 七、文件结构

```
frontend/
├── tests/
│   └── e2e/
│       ├── fixtures/
│       │   └── base.ts          ← 公共 fixture（页面跳转、截图辅助）
│       ├── pages/
│       │   ├── overview.spec.ts
│       │   ├── projects.spec.ts
│       │   ├── memory.spec.ts
│       │   ├── workflow.spec.ts
│       │   ├── checks.spec.ts
│       │   ├── scheduler.spec.ts
│       │   ├── wiki-home.spec.ts
│       │   ├── knowledge-graph.spec.ts
│       │   ├── lint-report.spec.ts
│       │   └── ingest.spec.ts
│       └── screenshots/         ← 自动生成
├── playwright.config.ts
```
