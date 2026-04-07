---
title: "自动化测试策略"
updated_at: 2026-04-07
---

# 自动化测试策略

## 测试分类

### Unit Tests — `tests/test_web_renderer.py`

测试 `renderer.py` 的纯函数，无 I/O：

| 用例 | 输入 | 断言 |
|------|------|------|
| Markdown 标题转 H1 | `"# Hello"` | HTML 含 `<h1>` |
| 代码块语法高亮 | `` "```python\nx=1```" `` | HTML 含 `<code>` |
| XSS 清除 | `"<script>alert(1)</script>"` | 输出不含 `<script>` |
| 空字符串 | `""` | 返回空字符串 |

### Integration Tests — `tests/test_web_api.py`

使用 `fastapi.testclient.TestClient`（同步，基于 `httpx`），所有测试隔离到临时目录。

**TestClient fixture:**
```python
@pytest.fixture
def client(tmp_path):
    # 在 tmp_path 写入 2 个 wiki 页面 + 1 个错误记录
    os.environ["AGENTS_MEMORY_ROOT"] = str(tmp_path)
    from agents_memory.web.api import app
    return TestClient(app)
```

**Phase 1 测试:**
- `test_stats_returns_counts` — stats.wiki_count == 2
- `test_wiki_list_all_topics` — topics 数组包含两个 slug
- `test_wiki_detail_ok` — 200，content_html 不为空
- `test_wiki_detail_not_found` — 404
- `test_wiki_lint_returns_list` — issues 是 list
- `test_errors_list` — errors 数组 >= 1
- `test_errors_detail_ok` — 200, content_html 不为空
- `test_errors_detail_not_found` — 404
- `test_rules_ok` — 200, raw 不为空

**Phase 2 测试:**
- `test_search_keyword` — results 包含匹配条目
- `test_search_empty_query_422` — q 缺失返回 422
- `test_ingest_dry_run` — dry_run=true，不写磁盘
- `test_wiki_put_compiled_truth` — 200，updated=true
- `test_ingest_log_returns_list` — entries 是 list

**Phase 3 测试:**
- `test_compile_returns_task_id` — 202，task_id 非空
- `test_task_status_pending` — status 在枚举内

## 覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| `agents_memory/web/api.py` | ≥ 85% |
| `agents_memory/web/renderer.py` | 100% |
| `agents_memory/web/models.py` | ≥ 80% |

运行: `pytest --cov=agents_memory/web --cov-report=term-missing tests/`

## CI 检查清单

```bash
# 1. 单元测试
pytest tests/test_web_renderer.py -v

# 2. 集成测试
pytest tests/test_web_api.py -v

# 3. 覆盖率
pytest --cov=agents_memory/web --cov-report=term-missing tests/

# 4. 类型检查（可选）
mypy agents_memory/web/ --ignore-missing-imports
```

## Bugfix 记录规范

发现 bug → 创建 `docs/bugfix/frontend/FE-XXX-short-desc.md`：

```markdown
# FE-001: /api/wiki/lint returns 500 when no wiki files

**发现时间:** 2026-04-07  
**严重级别:** medium  
**状态:** resolved

## 问题描述
当 wiki 目录为空时调用 /api/wiki/lint 返回 500。

## 根因
`os.listdir()` 在空目录返回 [] 正常，但代码假设至少存在一个文件。

## 修复
添加空列表守卫，直接返回 `{issues: [], total: 0}`。

## 防止复发
在测试用例 `test_wiki_lint_empty_dir` 中补充空目录场景。
```
