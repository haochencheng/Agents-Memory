#!/usr/bin/env bash
# scripts/web/manage.sh — categorized Agents-Memory Web service manager

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck disable=SC1091
source "$REPO_ROOT/scripts/lib/env.sh"

ENV_NAME="${AGENTS_MEMORY_ENV:-local}"
PRINT_JSON=false
POSITIONAL=()
while (($#)); do
  case "$1" in
    --env)
      ENV_NAME="${2:?missing env name after --env}"
      shift 2
      ;;
    --env=*)
      ENV_NAME="${1#*=}"
      shift
      ;;
    --json)
      PRINT_JSON=true
      shift
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL[@]}"

agents_memory_load_env "$REPO_ROOT" "$ENV_NAME"

if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
elif command -v python3.12 &>/dev/null; then
  PYTHON="python3.12"
else
  PYTHON="python3"
fi

API_PID_FILE="$REPO_ROOT/.web_api.${AGENTS_MEMORY_ENV}.pid"
UI_PID_FILE="$REPO_ROOT/.web_ui.${AGENTS_MEMORY_ENV}.pid"
API_LOG="$REPO_ROOT/logs/web-api.${AGENTS_MEMORY_ENV}.log"
UI_LOG="$REPO_ROOT/logs/web-ui.${AGENTS_MEMORY_ENV}.log"
API_PORT="${AGENTS_MEMORY_API_PORT:-10100}"
API_HOST="${AGENTS_MEMORY_API_HOST:-0.0.0.0}"
UI_PORT="${AGENTS_MEMORY_UI_PORT:-10000}"
UI_HOST="${AGENTS_MEMORY_UI_HOST:-0.0.0.0}"
API_PROXY_TARGET="${AGENTS_MEMORY_API_PROXY_TARGET:-http://localhost:${API_PORT}}"
FRONTEND_DIR="$REPO_ROOT/frontend"
API_BASE="http://localhost:$API_PORT"
REPLACE_COMPATIBLE_UI_ON_PORT="${REPLACE_COMPATIBLE_UI_ON_PORT:-false}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅  $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️   $*${NC}"; }
err()  { echo -e "${RED}❌  $*${NC}"; exit 1; }
info() { echo -e "${CYAN}ℹ️   $*${NC}"; }

mkdir -p "$REPO_ROOT/logs"

_pid_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

_clear_stale_pid_file() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]] && ! kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    rm -f "$pid_file"
  fi
}

_port_in_use() {
  lsof -ti tcp:"$1" &>/dev/null
}

_port_pid() {
  lsof -ti tcp:"$1" -sTCP:LISTEN 2>/dev/null | head -n 1
}

_pid_command() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

_is_agents_memory_api_pid() {
  local pid="$1"
  local cmd
  cmd="$(_pid_command "$pid")"
  [[ "$cmd" == *"uvicorn agents_memory.web.api:app"* ]]
}

_is_agents_memory_ui_pid() {
  local pid="$1"
  local cmd
  cmd="$(_pid_command "$pid")"
  [[ "$cmd" == *"$REPO_ROOT/frontend/node_modules/.bin/vite"* ]] || [[ "$cmd" == *"vite"*"$FRONTEND_DIR"* ]]
}

_api_supports_task_groups() {
  local body
  body="$(curl -fsS --max-time 5 "$API_BASE/openapi.json" 2>/dev/null || true)"
  [[ "$body" == *'"/api/scheduler/task-groups"'* ]]
}

_wait_for_api_contract() {
  local max_wait="${1:-15}"
  local elapsed=0
  while ! _api_supports_task_groups; do
    sleep 1
    elapsed=$((elapsed + 1))
    if (( elapsed >= max_wait )); then
      return 1
    fi
  done
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
  echo "=== 依赖检查 (${AGENTS_MEMORY_ENV}) ==="

  if ! command -v "$PYTHON" &>/dev/null; then
    err "Python 未找到。请先创建 .venv，或安装 python3.12 / python3"
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

_ensure_expected_api_on_port() {
  local pid
  pid="$(_port_pid "$API_PORT")"
  if [[ -z "$pid" ]]; then
    return 1
  fi

  if _api_supports_task_groups; then
    if _is_agents_memory_api_pid "$pid"; then
      echo "$pid" > "$API_PID_FILE"
      ok "检测到兼容的 Agents-Memory API 正在端口 $API_PORT 运行，已接管 PID $pid"
    else
      warn "端口 $API_PORT 上已有兼容 API 运行，但不由本脚本管理 (PID $pid)"
    fi
    return 0
  fi

  if _is_agents_memory_api_pid "$pid"; then
    warn "端口 $API_PORT 上的 Agents-Memory API 缺少 /api/scheduler/task-groups，正在替换旧进程 (PID $pid)"
    kill "$pid" 2>/dev/null || true
    sleep 1
    rm -f "$API_PID_FILE"
    return 1
  fi

  err "端口 $API_PORT 已被其他进程占用 (PID $pid)，且不是兼容的 Agents-Memory API；请先释放端口后再启动"
}

_ensure_expected_ui_on_port() {
  local pid
  pid="$(_port_pid "$UI_PORT")"
  if [[ -z "$pid" ]]; then
    return 1
  fi

  if _is_agents_memory_ui_pid "$pid"; then
    if [[ "$REPLACE_COMPATIBLE_UI_ON_PORT" == "true" ]]; then
      warn "端口 $UI_PORT 上已有兼容的 React 前端，正在替换旧进程 (PID $pid)"
      kill "$pid" 2>/dev/null || true
      sleep 1
      rm -f "$UI_PID_FILE"
      return 1
    fi
    echo "$pid" > "$UI_PID_FILE"
    ok "检测到兼容的 React 前端正在端口 $UI_PORT 运行，已接管 PID $pid"
    return 0
  fi

  err "端口 $UI_PORT 已被其他进程占用 (PID $pid)，且不是兼容的 Agents-Memory 前端；请先释放端口后再启动"
}

start_api() {
  _clear_stale_pid_file "$API_PID_FILE"
  if _pid_running "$API_PID_FILE"; then
    if _api_supports_task_groups; then
      warn "FastAPI 已在运行 (PID $(cat "$API_PID_FILE"))"
      return 0
    fi
    warn "PID 文件指向的 FastAPI 缺少新 scheduler 路由，正在重启 (PID $(cat "$API_PID_FILE"))"
    stop_service "$API_PID_FILE" "FastAPI"
  fi
  if _port_in_use "$API_PORT"; then
    if _ensure_expected_api_on_port; then
      return 0
    fi
  fi
  if _port_in_use "$API_PORT"; then
    warn "端口 $API_PORT 仍被占用，无法启动 FastAPI"
    return 1
  fi
  info "启动 FastAPI 后端 (${AGENTS_MEMORY_ENV}) → http://localhost:$API_PORT ..."
  cd "$REPO_ROOT"
  nohup env AGENTS_MEMORY_ENV="$AGENTS_MEMORY_ENV" AGENTS_MEMORY_ENV_FILE="$AGENTS_MEMORY_ENV_FILE" \
    AGENTS_MEMORY_API_PORT="$API_PORT" AGENTS_MEMORY_UI_PORT="$UI_PORT" \
    OLLAMA_HOST="${OLLAMA_HOST:-}" OLLAMA_PORT="${OLLAMA_PORT:-}" QDRANT_HOST="${QDRANT_HOST:-}" \
    QDRANT_PORT="${QDRANT_PORT:-}" QDRANT_GRPC_PORT="${QDRANT_GRPC_PORT:-}" \
    "$PYTHON" -m uvicorn agents_memory.web.api:app \
    --host "$API_HOST" --port "$API_PORT" \
    --log-level info \
    > "$API_LOG" 2>&1 &
  echo $! > "$API_PID_FILE"
  _wait_for_port "$API_PORT" "FastAPI" 30 || {
    warn "FastAPI 启动失败，查看日志: $API_LOG"
    return 1
  }
  _wait_for_api_contract 15 || {
    warn "FastAPI 已启动，但缺少 /api/scheduler/task-groups，查看日志: $API_LOG"
    return 1
  }
  ok "FastAPI 已启动 (PID $(cat "$API_PID_FILE"))"
  info "API Docs: http://localhost:$API_PORT/docs"
}

start_ui() {
  _clear_stale_pid_file "$UI_PID_FILE"
  if _pid_running "$UI_PID_FILE"; then
    warn "React 前端已在运行 (PID $(cat "$UI_PID_FILE"))"
    return 0
  fi
  if _port_in_use "$UI_PORT"; then
    if _ensure_expected_ui_on_port; then
      return 0
    fi
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
  info "启动 React 前端 (${AGENTS_MEMORY_ENV}) → http://localhost:$UI_PORT ..."
  cd "$FRONTEND_DIR"
  nohup env AGENTS_MEMORY_ENV="$AGENTS_MEMORY_ENV" AGENTS_MEMORY_ENV_FILE="$AGENTS_MEMORY_ENV_FILE" \
    AGENTS_MEMORY_API_PORT="$API_PORT" AGENTS_MEMORY_UI_PORT="$UI_PORT" \
    AGENTS_MEMORY_API_PROXY_TARGET="$API_PROXY_TARGET" \
    npm run dev -- --host "$UI_HOST" --port "$UI_PORT" \
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
    local pid
    pid=$(cat "$pid_file")
    kill "$pid" 2>/dev/null && ok "$label 已停止 (PID $pid)" || warn "无法停止 $label (PID $pid)"
    rm -f "$pid_file"
  else
    info "$label 未在运行"
    rm -f "$pid_file"
  fi
}

cmd_status() {
  echo ""
  echo "=== Web 服务状态 (${AGENTS_MEMORY_ENV}) ==="
  _clear_stale_pid_file "$API_PID_FILE"
  if _pid_running "$API_PID_FILE"; then
    if _api_supports_task_groups; then
      ok "FastAPI   ── 运行中 (PID $(cat "$API_PID_FILE")) → http://localhost:$API_PORT"
    else
      warn "FastAPI   ── PID $(cat "$API_PID_FILE") 在运行，但缺少 /api/scheduler/task-groups"
    fi
  elif _port_in_use "$API_PORT"; then
    local port_pid
    port_pid="$(_port_pid "$API_PORT")"
    if _api_supports_task_groups; then
      warn "FastAPI   ── 端口 $API_PORT 被兼容 API 占用（未写入 PID 文件，PID $port_pid）"
    else
      warn "FastAPI   ── 端口 $API_PORT 被旧版/未知进程占用 (PID $port_pid)"
    fi
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
  echo "=== 健康检查 (${AGENTS_MEMORY_ENV}) ==="
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
    "/api/scheduler/task-groups"
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

  local ui_status
  ui_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:$UI_PORT" 2>/dev/null || echo "000")
  if [[ "$ui_status" == "200" ]]; then
    ok "React UI → $ui_status"
  else
    warn "React UI → $ui_status（可能还在启动）"
  fi
}

cmd_config() {
  if [[ "$PRINT_JSON" == "true" ]]; then
    agents_memory_print_env_json
    return
  fi
  echo ""
  echo "=== Web Config (${AGENTS_MEMORY_ENV}) ==="
  echo "env file      : $AGENTS_MEMORY_ENV_FILE"
  echo "api host/port : $API_HOST:$API_PORT"
  echo "ui host/port  : $UI_HOST:$UI_PORT"
  echo "api proxy     : $API_PROXY_TARGET"
  echo "api pid file  : $API_PID_FILE"
  echo "ui pid file   : $UI_PID_FILE"
  echo "api log       : $API_LOG"
  echo "ui log        : $UI_LOG"
}

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
    REPLACE_COMPATIBLE_UI_ON_PORT=true
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
  config)
    cmd_config
    ;;
  *)
    echo "用法: bash scripts/web/manage.sh [--env local|staging|prod] [all|api|ui|stop|restart|status|health|config] [--json]"
    exit 1
    ;;
esac
