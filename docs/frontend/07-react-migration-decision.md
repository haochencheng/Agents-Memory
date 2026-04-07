---
created_at: 2026-04-07
updated_at: 2026-04-07
doc_status: active
---

# 前后端分离决策

## 结论（先读）

**当前阶段（v1）：保持 Streamlit MVP + FastAPI 不引入 React/npm。**  
**明确 Trigger 触发后再迁移到 React（见下方 Phase 2 条件）。**

---

## 现状评估

| 维度 | Streamlit MVP | React + Vite |
|------|--------------|-------------|
| 启动时间 | `pip install streamlit` 即可 | `npm install`（~30s）+ node 环境 |
| 构建产物 | 无，Python 直接运行 | 需 `npm run build` → dist/ |
| 运维复杂度 | 单进程 | 额外 node 进程 or nginx 静态托管 |
| 交互性 | 表单/表格/Markdown 足够 | 可做图表、拖拽、实时更新 |
| 代码量 | ~350 行 Python | ~2000+ 行 TypeScript + 配置文件 |
| 数据可视化 | st.dataframe、st.metric | D3.js/recharts 全能 |
| 离线可用 | ✅ | ❌（需 npm registry） |

**当前功能需求（5 个页面）完全在 Streamlit 能力范围内。**

---

## React 迁移 Trigger（满足任意一条时启动）

| # | 触发条件 |
|---|----------|
| T1 | 需要实时推送（WebSocket / SSE）展示 watcher 事件流 |
| T2 | 需要可交互 D3.js 知识图谱（wiki 话题关系图） |
| T3 | 需要多人协作（Auth + RBAC，Streamlit 不支持） |
| T4 | Wiki 编辑器需要富文本 / Markdown 实时预览（Monaco Editor）|
| T5 | 日均访问量 > 10 次（团队工具，不再是个人工具）|

---

## 如果触发迁移：推荐技术栈

```
React 18 + TypeScript
Vite 5 (构建工具，比 CRA 快 10x)
TailwindCSS v4 (样式)
TanStack Query v5 (数据获取 + 缓存)
React Router v6 (前端路由)
Zustand (轻量状态管理)
Recharts / D3.js (图表)
Vitest + Playwright (测试)
```

### 项目目录结构（迁移后）

```
agents_memory/
  web/           ← FastAPI 保持不变
  ui/            ← Streamlit 保持（不删，作为备用）

frontend/          ← 新增 React 项目
  package.json
  vite.config.ts
  src/
    main.tsx
    pages/
      Overview.tsx
      Wiki.tsx
      Search.tsx
      Errors.tsx
      Ingest.tsx
    components/
    api/           ← fetch wrappers (generated from openapi.json)
  tests/
    e2e/           ← Playwright tests
```

### API 代码生成

FastAPI 提供 `/openapi.json`，可直接生成 TypeScript 客户端：

```bash
npx @hey-api/openapi-ts \
  -i http://localhost:10100/openapi.json \
  -o frontend/src/api \
  -c @hey-api/client-fetch
```

每次 API schema 变更后重新生成，保持前后端类型对齐。

---

## 不引入的理由（技术债）

- npm 依赖树 (`node_modules/`) — 锁定版本复杂，安全漏洞扫描成本高
- 前后端两套语言（Python + TypeScript）增加认知负担
- 本工具定位是**个人/小团队本地工具**，Streamlit 完全够用
- React 增加 CI 复杂度（node cache、build step、bundle check）

---

## 当前行动项

- [x] 保持 Streamlit MVP，不引入 npm
- [x] FastAPI `/openapi.json` 已可用（FastAPI 自动生成）
- [ ] 在 `docs/frontend/04-plans.md` Phase 5 添加 React 迁移阶段（待触发条件满足后）
- [ ] 当 T1-T5 中任何一条触发时，新建分支 `feat/react-ui`，按上方技术栈实施
