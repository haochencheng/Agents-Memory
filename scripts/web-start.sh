#!/usr/bin/env bash
# scripts/web-start.sh — Agents-Memory Web 服务启动脚本
#
# 用法:
#   bash scripts/web-start.sh            # 启动 API + React 前端
#   bash scripts/web-start.sh api        # 只启动 FastAPI 后端
#   bash scripts/web-start.sh ui         # 只启动 React 前端 (Vite dev)
#   bash scripts/web-start.sh stop       # 停止所有 Web 服务
#   bash scripts/web-start.sh status     # 检查服务状态
#   bash scripts/web-start.sh health     # 调用健康检查接口并打印结果
#   bash scripts/web-start.sh restart    # 重启所有 Web 服务
#
# 架构:
#   FastAPI  :10100  — REST API 后端
#   React    :10000  — Vite 开发服务器 (SPA 前端)
#
# 依赖:
#   python3.12, pip (fastapi, uvicorn, requests)
#   node >= 18, npm

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="python3.12"
API_PID_FILE="$REPO_ROOT/.web_api.pid"
UI_PID_FILE="$REPO_ROOT/.web_ui.pid"
API_LOG="$REPO_ROOT/logs/web-api.log"
UI_LOG="$REPO_ROOT/logs/web-ui.log"
API_PORT="${AGENTS_MEMORY_API_PORT:-10100}"
UI_PORT="${AGENTS_MEMORY_UI_PORT:-10000}"
FRONTEND_DIR="$REPO_ROOT/frontend"
API_BASE="http://localhost:$API_PORT"

# ─── 颜色 ─────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅  $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️   $*${NC}"; }
err()  { echo -e "${RED}❌  $*${NC}"; exit 1; }
info() { echo -e "${CYAN}ℹ️   $*${NC}"; }

# ─── 工具函数 ─────────────────────────────────────────────────────────────────

mkdir -p "$REPO_ROOT/logs"

_pid_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

_port_in_use() {
  lsof -ti tcp:"$1" &>/dev/null
}

_wait_for_port() {
  local port="$1" label="$2" max_wait="${3:-30}"
  local elapsed=0
  info "等待 $label 在端口 $port 启动..."
  while ! _port_in_use "$port"; do
    sleep 1
    elapsed=$((elapsed + 1))
    if (( elapsed >= max_wait )); then
      warn "$label 在 ${max_wait}s 内未能在端口 $port 上响应"
      return 1
    fi
    printf "."
  done
  echo ""
  ok "$label 已在端口 $port 上就绪（${elapsed}s）"
}

_check_deps() {
  echo ""
  echo "=== 依赖检查 ==="

  if ! command -v "$PYTHON" &>/dev/null; then
    err "Python 3.12 未找到。安装: brew install python@3.12"
  fi
  ok "Python: $($PYTHON --version)"

  if ! command -v node &>/dev/null; then
    err "Node.js 未找到。请安装 Node >= 18"
  fi
  if ! command -v npm &>/dev/null; then
    err "npm 未找到。请安装 npm"
  fi
  ok "Node: $(node --version)"
  ok "npm: $(npm --version)"

  local missing=()
  for pkg in fastapi uvicorn requests; do
    if ! $PYTHON -c "import ${pkg//-/_}" 2>/dev/null; then
      missing+=("$pkg")
    fi
  done

  if (( ${#missing[@]} > 0 )); then
    warn "缺少依赖: ${missing[*]}，正在安装..."
    $PYTHON -m pip install "${missing[@]}" "uvicorn[standard]" --break-system-packages -q
    ok "依赖安装完成"
  else
    ok "所有依赖已安装"
  fi
}

# ─── 服务控制 ─────────────────────────────────────────────────────────────────

start_api() {
  if _pid_running "$API_PID_FILE"; then
    warn "FastAPI 已在运行 (PID $(cat "$API_PID_FILE"))"
    return 0
  fi
  if _port_in_use "$API_PORT"; then
    warn "端口 $API_PORT 已被占用（可能已有 API 运行）"
    return 0
  fi
  info "启动 FastAPI 后端 → http://localhost:$API_PORT ..."
  cd "$REPO_ROOT"
  nohup $PYTHON -m uvicorn agents_memory.web.api:app \
    --host 0.0.0.0 --port "$API_PORT" \
    --log-level info \
    > "$API_LOG" 2>&1 &
  echo $! > "$API_PID_FILE"
  _wait_for_port "$API_PORT" "FastAPI" 30 || {
    warn "FastAPI 启动失败，查看日志: $API_LOG"
    return 1
  }
  ok "FastAPI 已启动 (PID $(cat "$API_PID_FILE"))"
  info "API Docs: http://localhost:$API_PORT/docs"
}

start_ui() {
  if _pid_running "$UI_PID_FILE"; then
    warn "React 前端已在运行 (PID $(cat "$UI_PID_FILE"))"
    return 0
  fi
  if _port_in_use "$UI_PORT"; then
    warn "端口 $UI_PORT 已被占用（可能已有前端运行）"
    return 0
  fi
  if [[ ! -d "$FRONTEND_DIR" ]]; then
    err "frontend/ 目录不存在"
  fi
  if [[ ! -f "$FRONTEND_DIR/package.json" ]]; then
    err "frontend/package.json 不存在"
  fi
  if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    warn "frontend/node_modules 不存在，正在安装前端依赖..."
    cd "$FRONTEND_DIR"
    npm install > "$UI_LOG" 2>&1
  fi
  info "启动 React 前端 → http://localhost:$UI_PORT ..."
  cd "$FRONTEND_DIR"
  nohup npm run dev -- --host 0.0.0.0 --port "$UI_PORT" \
    > "$UI_LOG" 2>&1 &
  echo $! > "$UI_PID_FILE"
  _wait_for_port "$UI_PORT" "React 前端" 30 || {
    warn "React 前端启动失败，查看日志: $UI_LOG"
    return 1
  }
  ok "React 前端已启动 (PID $(cat "$UI_PID_FILE"))"
  info "UI: http://localhost:$UI_PORT"
}

stop_service() {
  local pid_file="$1" label="$2"
  if _pid_running "$pid_file"; then
    local pid; pid=$(cat "$pid_file")
    kill "$pid" 2>/dev/null && ok "$label 已停止 (PID $pid)" || warn "无法停止 $label (PID $pid)"
    rm -f "$pid_file"
  else
    info "$label 未在运行"
    rm -f "$pid_file"
  fi
}

cmd_status() {
  echo ""
  echo "=== Web 服务状态 ==="
  if _pid_running "$API_PID_FILE"; then
    ok "FastAPI   ── 运行中 (PID $(cat "$API_PID_FILE")) → http://localhost:$API_PORT"
  elif _port_in_use "$API_PORT"; then
    warn "FastAPI   ── 端口 $API_PORT 被占用（不由本脚本管理）"
  else
    echo -e "${RED}❌  FastAPI   ── 未运行${NC}"
  fi

  if _pid_running "$UI_PID_FILE"; then
    ok "React UI  ── 运行中 (PID $(cat "$UI_PID_FILE")) → http://localhost:$UI_PORT"
  elif _port_in_use "$UI_PORT"; then
    warn "React UI  ── 端口 $UI_PORT 被占用（不由本脚本管理）"
  else
    echo -e "${RED}❌  React UI  ── 未运行${NC}"
  fi
  echo ""
}

cmd_health() {
  echo ""
  echo "=== 健康检查 ==="
  if ! command -v curl &>/dev/null; then
    warn "curl 未安装，使用 python requests 代替"
    $PYTHON -c "
import sys, urllib.request, json
try:
    r = urllib.request.urlopen('http://localhost:$API_PORT/api/stats', timeout=5)
    data = json.loads(r.read())
    print(f'  ✅  API /api/stats OK — wiki:{data[\"wiki_count\"]} errors:{data[\"error_count\"]} ingest:{data[\"ingest_count\"]}')
except Exception as e:
    print(f'  ❌  API /api/stats FAIL — {e}')
    sys.exit(1)
"
    return
  fi

  local endpoints=(
    "/api/stats"
    "/api/wiki"
    "/api/wiki/lint"
    "/api/errors"
    "/api/rules"
    "/api/ingest/log"
  )
  local ok_count=0 fail_count=0
  for ep in "${endpoints[@]}"; do
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$API_BASE$ep" 2>/dev/null || echo "000")
    if [[ "$status" == "200" ]]; then
      ok "GET $ep → $status"
      ok_count=$((ok_count + 1))
    else
      echo -e "${RED}❌  GET $ep → $status${NC}"
      fail_count=$((fail_count + 1))
    fi
  done

  echo ""
  if (( fail_count == 0 )); then
    ok "所有 $ok_count 个健康检查通过"
  else
    warn "$ok_count 通过 / $fail_count 失败"
    return 1
  fi

  # React UI ping
  local ui_status
  ui_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:$UI_PORT" 2>/dev/null || echo "000")
  if [[ "$ui_status" == "200" ]]; then
    ok "React UI → $ui_status"
  else
    warn "React UI → $ui_status（可能还在启动）"
  fi
}

# ─── 主命令分发 ───────────────────────────────────────────────────────────────

CMD="${1:-all}"

case "$CMD" in
  all)
    _check_deps
    start_api
    start_ui
    cmd_status
    cmd_health
    ;;
  api)
    _check_deps
    start_api
    ;;
  ui)
    start_ui
    ;;
  stop)
    stop_service "$API_PID_FILE" "FastAPI"
    stop_service "$UI_PID_FILE" "React 前端"
    cmd_status
    ;;
  restart)
    stop_service "$API_PID_FILE" "FastAPI"
    stop_service "$UI_PID_FILE" "React 前端"
    sleep 1
    _check_deps
    start_api
    start_ui
    cmd_status
    cmd_health
    ;;
  status)
    cmd_status
    ;;
  health)
    cmd_health
    ;;
  *)
    echo "用法: bash scripts/web-start.sh [all|api|ui|stop|restart|status|health]"
    exit 1
    ;;
esac
