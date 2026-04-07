"""Agents-Memory Web UI — Streamlit MVP.

Start:
    streamlit run agents_memory/ui/streamlit_app.py --server.port 8501

Requires FastAPI backend running at http://localhost:10100.
Falls back to direct service calls when API is unreachable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

try:
    import streamlit as st
except ImportError:
    raise SystemExit("streamlit not installed. Run: pip install streamlit>=1.32")

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE = os.environ.get("AGENTS_MEMORY_API", "http://localhost:10100")

st.set_page_config(
    page_title="Agents-Memory",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def _api(path: str, method: str = "GET", **kwargs):
    """Call API. Returns (data_dict | None, error_str | None)."""
    if requests is None:
        return None, "requests not installed"
    try:
        url = f"{API_BASE}{path}"
        resp = getattr(requests, method.lower())(url, timeout=10, **kwargs)
        if resp.status_code == 200 or resp.status_code == 202:
            return resp.json(), None
        return None, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as exc:
        return None, str(exc)


# ---------------------------------------------------------------------------
# Page: 概览
# ---------------------------------------------------------------------------


def _render_wiki_lint_section() -> None:
    """Fetch wiki lint results and render warnings or OK badge."""
    st.subheader("Wiki Lint 检查")
    lint_data, lint_err = _api("/api/wiki/lint")
    if lint_err:
        st.warning(f"Lint 检查失败: {lint_err}")
        return
    if not lint_data:
        return
    issues = lint_data.get("issues", [])
    total = lint_data.get("total", 0)
    if total == 0:
        st.success("✅ 无 Lint 问题")
        return
    st.warning(f"发现 {total} 个问题")
    for issue in issues[:10]:
        level = issue.get("level", "warning")
        icon = "🔴" if level == "error" else "🟡"
        st.write(f"{icon} `{issue.get('topic')}` — {issue.get('message')}")


def page_overview() -> None:
    """Overview page: stats + project badges + wiki lint summary.

    # Two sections: (1) metrics/projects from /api/stats; (2) lint via _render_wiki_lint_section.
    """
    st.header("🧠 Agents-Memory — 概览")
    data, err = _api("/api/stats")
    if err:
        st.error(f"无法连接到 API: {err}")
        st.info(f"请确保后端运行在 {API_BASE}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Wiki 话题数", data.get("wiki_count", 0))
    col2.metric("错误记录数", data.get("error_count", 0))
    col3.metric("已摄入文档数", data.get("ingest_count", 0))

    projects = data.get("projects", [])
    if projects:
        st.subheader("项目列表")
        for p in projects:
            st.badge(p)

    st.divider()
    _render_wiki_lint_section()


# ---------------------------------------------------------------------------
# Page: Wiki 浏览
# ---------------------------------------------------------------------------


def _render_wiki_detail(selected_topic: str) -> None:
    """Load and render wiki page detail in the right panel."""
    detail, detail_err = _api(f"/api/wiki/{selected_topic}")
    if detail_err:
        st.error(f"加载 '{selected_topic}' 失败: {detail_err}")
        return
    st.subheader(detail.get("title", selected_topic))
    fm = detail.get("frontmatter", {})
    if fm:
        cols = st.columns(min(len(fm), 4))
        for i, (k, v) in enumerate(list(fm.items())[:4]):
            cols[i].caption(f"**{k}**: {v}")
    tab_rendered, tab_raw = st.tabs(["渲染视图", "原始 Markdown"])
    with tab_rendered:
        st.markdown(detail.get("content_html", ""), unsafe_allow_html=True)
    with tab_raw:
        st.code(detail.get("raw", ""), language="markdown")


def page_wiki() -> None:
    """Wiki browser page: topic list (left) + detail view (right).

    # Left: filtered list of topics with session_state selection; right: _render_wiki_detail.
    """
    st.header("📚 Wiki 知识库")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("话题列表")
        data, err = _api("/api/wiki")
        if err:
            st.error(f"获取 Wiki 列表失败: {err}")
            return

        topics = data.get("topics", [])
        if not topics:
            st.info("Wiki 目录为空")
            return

        search_q = st.text_input("过滤话题", placeholder="输入关键词...")
        filtered = [t for t in topics if not search_q or search_q.lower() in t["topic"].lower() or search_q.lower() in t["title"].lower()]

        for t in filtered:
            label = f"**{t['title']}**\n_{t['topic']}_ · {t['word_count']} 词"
            if st.button(label, key=f"wiki_{t['topic']}", use_container_width=True):
                st.session_state["wiki_selected"] = t["topic"]

    with col_right:
        selected_topic = st.session_state.get("wiki_selected")
        if selected_topic:
            _render_wiki_detail(selected_topic)
        else:
            st.info("← 选择左侧话题查看内容")


# ---------------------------------------------------------------------------
# Page: 搜索
# ---------------------------------------------------------------------------


def page_search() -> None:
    """Hybrid search page: query input + mode selector → call /api/search → render results.

    # Input widgets → API call on submit → loop results into expanders with snippet.
    """
    st.header("🔍 混合搜索")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("搜索内容", placeholder="输入关键词或问题...")
    with col2:
        mode = st.selectbox("搜索模式", ["hybrid", "keyword", "semantic"])

    if st.button("搜索", type="primary") and query:
        data, err = _api(f"/api/search?q={query}&mode={mode}&limit=20")
        if err:
            st.error(f"搜索失败: {err}")
            return

        results = data.get("results", [])
        total = data.get("total", 0)
        st.caption(f"共找到 {total} 条结果（模式: {mode}）")

        for r in results:
            rtype = r.get("type", "")
            icon = "📚" if rtype == "wiki" else "🐛"
            with st.expander(f"{icon} {r.get('title', r.get('id', ''))} — score: {r.get('score', 0):.3f}"):
                st.caption(f"类型: {rtype} | ID: {r.get('id', '')}")
                if r.get("snippet"):
                    st.markdown(f"> {r.get('snippet')}")
    elif query == "":
        st.info("输入关键词并点击搜索")


# ---------------------------------------------------------------------------
# Page: 错误记录
# ---------------------------------------------------------------------------


def _render_errors_table(errors: list) -> None:
    """Display errors as a dataframe (pandas) or text fallback."""
    import pandas as pd  # noqa: PLC0415 — optional dependency
    try:
        df = pd.DataFrame(errors)
        cols = [c for c in ["id", "title", "status", "project", "severity", "created_at"] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
    except ImportError:
        _ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        for e in errors:
            icon = _ICON.get(e.get("severity", ""), "⚪")
            st.write(f"{icon} `{e.get('id', '')}` — {e.get('title', '')} [{e.get('status', '')}]")


def _render_error_detail_lookup() -> None:
    """ID-text-input + button to load a single error record."""
    error_id = st.text_input("输入错误 ID")
    if error_id and st.button("查看"):
        detail, detail_err = _api(f"/api/errors/{error_id}")
        if detail_err:
            st.error(f"找不到 '{error_id}': {detail_err}")
        else:
            st.subheader(detail.get("title", error_id))
            st.caption(f"状态: {detail.get('status')} | 项目: {detail.get('project')} | 时间: {detail.get('created_at')}")
            st.markdown(detail.get("content_html", ""), unsafe_allow_html=True)


def page_errors() -> None:
    """Error records page: filter sidebar → table → detail lookup.

    # Three sections: (1) sidebar filters; (2) _render_errors_table; (3) _render_error_detail_lookup.
    """
    st.header("🐛 错误记录")

    with st.sidebar:
        st.subheader("过滤器")
        status_filter = st.selectbox("状态", ["", "new", "reviewed", "resolved", "archived"], index=0)
        project_filter = st.text_input("项目名")

    qs = "?" + (f"status={status_filter}&" if status_filter else "") + (f"project={project_filter}&" if project_filter else "") + "limit=100"
    data, err = _api(f"/api/errors{qs}")
    if err:
        st.error(f"获取错误记录失败: {err}")
        return

    errors = data.get("errors", [])
    st.caption(f"共 {data.get('total', 0)} 条记录")
    if not errors:
        st.info("没有匹配的错误记录")
        return

    _render_errors_table(errors)
    st.divider()
    st.subheader("查看详情")
    _render_error_detail_lookup()


# ---------------------------------------------------------------------------
# Page: Ingest
# ---------------------------------------------------------------------------


def _handle_ingest_submit(source_type: str, project: str, content: str, dry_run: bool) -> None:
    """Submit ingest form data to the API and render the outcome."""
    if not content.strip():
        st.warning("文档内容不能为空")
        return
    payload = {
        "content": content,
        "source_type": source_type,
        "project": project,
        "dry_run": dry_run,
    }
    data, err = _api("/api/ingest", method="POST", json=payload)
    if err:
        st.error(f"摄入失败: {err}")
    elif data.get("dry_run"):
        st.info(f"演习模式：验证通过，实际不写入。（ID 将会是: {data.get('id', 'auto-generated')}）")
    else:
        st.success(f"✅ 摄入成功！记录 ID: `{data.get('id')}`")


def _render_ingest_log() -> None:
    """Fetch and display the last 20 ingest log entries."""
    log_data, log_err = _api("/api/ingest/log?limit=20")
    if log_err:
        st.warning(f"无法获取日志: {log_err}")
        return
    if not log_data:
        return
    entries = log_data.get("entries", [])
    if entries:
        for e in entries:
            icon = "✅" if e.get("status") == "ok" else "❌"
            st.write(f"{icon} `{e.get('ts', '')}` — {e.get('source_type', '')} / {e.get('project', '')} → `{e.get('id', '')}`")
    else:
        st.info("暂无摄入记录")


def page_ingest() -> None:
    """Ingest page: form to submit documents + log viewer.

    # Two sections: (1) submission form → _handle_ingest_submit; (2) log viewer → _render_ingest_log.
    """
    st.header("📥 摄入文档")

    with st.form("ingest_form"):
        source_type = st.selectbox(
            "文档类型",
            ["error_record", "pr-review", "meeting", "decision", "code-review"],
        )
        project = st.text_input("项目名", placeholder="synapse-network")
        content = st.text_area(
            "文档内容（Markdown）",
            height=300,
            placeholder="## 问题描述\n\n粘贴你的文档内容...",
        )
        dry_run = st.checkbox("演习模式（不写入磁盘）", value=True)
        submitted = st.form_submit_button("摄入", type="primary")

    if submitted:
        _handle_ingest_submit(source_type, project, content, dry_run)

    st.divider()
    st.subheader("摄入日志")
    if st.button("刷新日志"):
        st.session_state["refresh_log"] = True

    _render_ingest_log()


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------


def main() -> None:
    with st.sidebar:
        st.title("🧠 Agents-Memory")
        st.caption(f"API: {API_BASE}")
        st.divider()
        page = st.radio(
            "导航",
            ["概览", "Wiki", "搜索", "错误记录", "Ingest"],
            label_visibility="collapsed",
        )

    if page == "概览":
        page_overview()
    elif page == "Wiki":
        page_wiki()
    elif page == "搜索":
        page_search()
    elif page == "错误记录":
        page_errors()
    elif page == "Ingest":
        page_ingest()


if __name__ == "__main__":
    main()
else:
    # Streamlit runs module-level code on import
    main()
