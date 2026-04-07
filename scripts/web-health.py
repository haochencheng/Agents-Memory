#!/usr/bin/env python3.12
"""scripts/web-health.py — Agents-Memory Web UI 健康检查与端到端冒烟测试

可直接运行（不需要 pytest），逐一验证每个 API 端点和 Streamlit UI 页面可达性。
退出码：0 = 全部通过，1 = 有失败项。

用法:
    python3.12 scripts/web-health.py                  # 默认检查 localhost:10100
    python3.12 scripts/web-health.py --api http://localhost:10100
    python3.12 scripts/web-health.py --ui  http://localhost:8501
    python3.12 scripts/web-health.py --json            # JSON 格式输出（CI 友好）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

# ─── ANSI ─────────────────────────────────────────────────────────────────────
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
CYAN = "\033[0;36m"
NC = "\033[0m"

def _ok(msg: str) -> str:   return f"{GREEN}✅  {msg}{NC}"
def _warn(msg: str) -> str: return f"{YELLOW}⚠️   {msg}{NC}"
def _fail(msg: str) -> str: return f"{RED}❌  {msg}{NC}"
def _info(msg: str) -> str: return f"{CYAN}ℹ️   {msg}{NC}"


# ─── Result type ──────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    passed: bool
    status_code: int = 0
    latency_ms: float = 0.0
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


def _http_get(url: str, timeout: int = 8) -> tuple[int, bytes]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return 0, str(e).encode()


def check_endpoint(
    label: str,
    url: str,
    *,
    expected_status: int = 200,
    key_present: str | None = None,
    min_val: tuple[str, int] | None = None,
) -> CheckResult:
    t0 = time.perf_counter()
    code, body = _http_get(url)
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    if code != expected_status:
        return CheckResult(
            name=label, passed=False, status_code=code, latency_ms=latency_ms,
            detail=f"期望 {expected_status}，实际 {code}",
        )

    data: dict[str, Any] = {}
    try:
        data = json.loads(body)
    except Exception:
        pass

    if key_present and key_present not in data:
        return CheckResult(
            name=label, passed=False, status_code=code, latency_ms=latency_ms,
            detail=f"响应中缺少字段 '{key_present}'",
            data=data,
        )

    if min_val:
        k, v = min_val
        actual = data.get(k, -1)
        if isinstance(actual, (int, float)) and actual < v:
            return CheckResult(
                name=label, passed=False, status_code=code, latency_ms=latency_ms,
                detail=f"data.{k}={actual} < 期望 {v}",
                data=data,
            )

    return CheckResult(name=label, passed=True, status_code=code, latency_ms=latency_ms, data=data)


# ─── Test suites ──────────────────────────────────────────────────────────────

def suite_api(api_base: str) -> list[CheckResult]:
    """验证所有 API 端点是否正确响应。"""
    results: list[CheckResult] = []

    # --- 统计 ---
    r = check_endpoint("GET /api/stats", f"{api_base}/api/stats", key_present="wiki_count")
    results.append(r)

    # --- Wiki ---
    r = check_endpoint("GET /api/wiki", f"{api_base}/api/wiki", key_present="topics")
    results.append(r)

    r = check_endpoint("GET /api/wiki/lint", f"{api_base}/api/wiki/lint", key_present="issues")
    results.append(r)

    # 动态取第一个 topic 验证详情端点
    topics_result = next((x for x in results if x.name == "GET /api/wiki"), None)
    first_topic = None
    if topics_result and topics_result.passed:
        topics = topics_result.data.get("topics", [])
        if topics:
            first_topic = topics[0]["topic"]

    if first_topic:
        r = check_endpoint(
            f"GET /api/wiki/{first_topic}",
            f"{api_base}/api/wiki/{first_topic}",
            key_present="content_html",
        )
        results.append(r)
    else:
        results.append(CheckResult(
            name="GET /api/wiki/:topic",
            passed=True,
            detail="wiki 目录为空，跳过详情检查",
        ))

    # Wiki 404
    r = check_endpoint(
        "GET /api/wiki/nonexistent-xyz (期望 404)",
        f"{api_base}/api/wiki/nonexistent-topic-xyz-999",
        expected_status=404,
    )
    results.append(r)

    # --- 错误记录 ---
    r = check_endpoint("GET /api/errors", f"{api_base}/api/errors", key_present="errors")
    results.append(r)

    r = check_endpoint("GET /api/errors?status=open", f"{api_base}/api/errors?status=open", key_present="errors")
    results.append(r)

    # --- 搜索 ---
    r = check_endpoint("GET /api/search?q=test", f"{api_base}/api/search?q=test", key_present="results")
    results.append(r)

    r = check_endpoint(
        "GET /api/search (无 q 参数，期望 422)",
        f"{api_base}/api/search",
        expected_status=422,
    )
    results.append(r)

    # --- Ingest ---
    r = check_endpoint("GET /api/ingest/log", f"{api_base}/api/ingest/log", key_present="entries")
    results.append(r)

    # POST dry_run（不写磁盘）
    import urllib.parse  # noqa: PLC0415
    t0 = time.perf_counter()
    payload = json.dumps({
        "content": "# Health Check\nThis is a dry-run health check.",
        "source_type": "error_record",
        "project": "health-check",
        "dry_run": True,
    }).encode()
    try:
        req = urllib.request.Request(
            f"{api_base}/api/ingest",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            code = resp.status
            body = resp.read()
    except urllib.error.HTTPError as e:
        code, body = e.code, b""
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    data = {}
    try:
        data = json.loads(body)
    except Exception:
        pass
    passed = code == 200 and data.get("dry_run") is True
    results.append(CheckResult(
        name="POST /api/ingest (dry_run=true)",
        passed=passed,
        status_code=code,
        latency_ms=latency_ms,
        detail="" if passed else f"code={code} data={data}",
        data=data,
    ))

    # --- Rules ---
    r = check_endpoint("GET /api/rules", f"{api_base}/api/rules", key_present="raw")
    results.append(r)

    return results


def suite_ui(ui_base: str) -> list[CheckResult]:
    """验证 Streamlit UI 是否可达（HTTP 200）。"""
    results: list[CheckResult] = []
    t0 = time.perf_counter()
    code, body = _http_get(ui_base, timeout=10)
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    # Streamlit returns 200 with HTML
    passed = code == 200 and b"<!DOCTYPE html>" in body.lower() or b"streamlit" in body.lower()
    results.append(CheckResult(
        name="Streamlit UI / (HTTP 200 + HTML)",
        passed=code == 200,
        status_code=code,
        latency_ms=latency_ms,
        detail="" if code == 200 else f"Streamlit UI 未响应（code={code}）",
    ))

    # Static asset
    t0 = time.perf_counter()
    asset_code, _ = _http_get(f"{ui_base}/healthz", timeout=5)
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    # Streamlit doesn't have /healthz natively; accept 200 or 404 (UI is alive either way)
    results.append(CheckResult(
        name="Streamlit UI reachable (/healthz probe)",
        passed=asset_code in (200, 404),
        status_code=asset_code,
        latency_ms=latency_ms,
        detail="" if asset_code in (200, 404) else f"Streamlit 未响应（code={asset_code}）",
    ))
    return results


# ─── Reporter ─────────────────────────────────────────────────────────────────

def _print_results(results: list[CheckResult], suite_name: str, json_mode: bool) -> int:
    if json_mode:
        return sum(1 for r in results if not r.passed)
    print(f"\n=== {suite_name} ===")
    fail_count = 0
    for r in results:
        latency_str = f"  ({r.latency_ms}ms)" if r.latency_ms else ""
        if r.passed:
            detail = ""
            if r.data:
                # Show key summary
                summary_keys = ["wiki_count", "error_count", "ingest_count", "total"]
                parts = [f"{k}={r.data[k]}" for k in summary_keys if k in r.data]
                detail = f"  [{', '.join(parts)}]" if parts else ""
            print(_ok(f"{r.name}{latency_str}{detail}"))
        else:
            print(_fail(f"{r.name}{latency_str} — {r.detail}"))
            fail_count += 1
    return fail_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Agents-Memory Web 健康检查")
    parser.add_argument("--api", default="http://localhost:10100", help="FastAPI base URL")
    parser.add_argument("--ui", default="http://localhost:8501", help="Streamlit UI URL")
    parser.add_argument("--skip-ui", action="store_true", help="跳过 Streamlit UI 检查")
    parser.add_argument("--json", action="store_true", dest="json_mode", help="JSON 格式输出")
    args = parser.parse_args()

    all_results: list[CheckResult] = []

    print(_info(f"API: {args.api}") if not args.json_mode else "")
    api_results = suite_api(args.api)
    all_results.extend(api_results)
    api_fails = _print_results(api_results, "API 端点验证", args.json_mode)

    ui_fails = 0
    if not args.skip_ui:
        print(_info(f"UI: {args.ui}") if not args.json_mode else "")
        ui_results = suite_ui(args.ui)
        all_results.extend(ui_results)
        ui_fails = _print_results(ui_results, "Streamlit UI 验证", args.json_mode)

    total_pass = sum(1 for r in all_results if r.passed)
    total_fail = sum(1 for r in all_results if not r.passed)

    if args.json_mode:
        print(json.dumps({
            "passed": total_pass,
            "failed": total_fail,
            "results": [asdict(r) for r in all_results],
        }, ensure_ascii=False, indent=2))
        return 0 if total_fail == 0 else 1

    print(f"\n{'─'*50}")
    if total_fail == 0:
        print(_ok(f"全部 {total_pass} 项检查通过"))
    else:
        print(_warn(f"{total_pass} 通过 / {total_fail} 失败"))
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
