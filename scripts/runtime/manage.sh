#!/usr/bin/env bash
# scripts/runtime/manage.sh — categorized runtime service manager

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

MCP_SERVER="$REPO_ROOT/scripts/mcp_server.py"
DOCKER_DIR="$REPO_ROOT/docker"
MCP_PID_FILE="$REPO_ROOT/.mcp_server.${AGENTS_MEMORY_ENV}.pid"
LOG_FILE="$REPO_ROOT/logs/agents-memory.${AGENTS_MEMORY_ENV}.log"

compose() {
  if command -v docker-compose &>/dev/null; then
    docker-compose "$@"
  else
    docker compose "$@"
  fi
}

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { printf "%b\n" "${GREEN}✅  $*${NC}"; }
warn() { printf "%b\n" "${YELLOW}⚠️   $*${NC}"; }
err()  { printf "%b\n" "${RED}❌  $*${NC}"; }
info() { printf "    %s\n" "$*"; }

check_deps() {
  echo ""
  echo "=== 依赖检查 (${AGENTS_MEMORY_ENV}) ==="

  if command -v "$PYTHON" &>/dev/null; then
    ok "Python: $($PYTHON --version)"
  else
    err "Python 未找到。请先创建 .venv，或安装 python3.12 / python3"
    exit 1
  fi

  if $PYTHON -c "from mcp.server.fastmcp import FastMCP" 2>/dev/null; then
    ok "mcp package: installed"
  else
    warn "mcp 未安装，正在安装..."
    $PYTHON -m pip install mcp --break-system-packages -q
    ok "mcp package: installed"
  fi

  if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    ok "Docker: $(docker --version | head -1)"
    DOCKER_OK=true
  else
    warn "Docker 未运行（Qdrant/Ollama 不可用）"
    DOCKER_OK=false
  fi
}

start_qdrant() {
  echo ""
  echo "=== 启动 Qdrant (${AGENTS_MEMORY_ENV}) ==="
  if [[ "${DOCKER_OK:-false}" != "true" ]]; then
    warn "Docker 未就绪，跳过 Qdrant。"
    return
  fi

  mkdir -p "$DOCKER_DIR/data/qdrant"
  cd "$DOCKER_DIR"
  QDRANT_PORT="${QDRANT_PORT:-6333}" QDRANT_GRPC_PORT="${QDRANT_GRPC_PORT:-6334}" compose up -d qdrant

  printf "    等待 Qdrant 就绪"
  for _ in $(seq 1 30); do
    if curl -sf "http://localhost:${QDRANT_PORT:-6333}/readyz" &>/dev/null; then
      echo ""
      ok "Qdrant: http://localhost:${QDRANT_PORT:-6333}"
      cd "$REPO_ROOT"
      return
    fi
    printf "."
    sleep 1
  done
  echo ""
  err "Qdrant 启动超时。查看日志: docker-compose logs qdrant"
  cd "$REPO_ROOT"
}

start_ollama() {
  echo ""
  echo "=== 启动 Ollama (${AGENTS_MEMORY_ENV}) ==="
  if [[ "${DOCKER_OK:-false}" != "true" ]]; then
    warn "Docker 未就绪，跳过 Ollama。"
    return
  fi

  mkdir -p "$DOCKER_DIR/data/ollama"
  cd "$DOCKER_DIR"
  OLLAMA_PORT="${OLLAMA_PORT:-11434}" compose up -d ollama

  printf "    等待 Ollama 就绪"
  for _ in $(seq 1 45); do
    if curl -sf "http://localhost:${OLLAMA_PORT:-11434}/api/tags" &>/dev/null; then
      echo ""
      ok "Ollama: http://localhost:${OLLAMA_PORT:-11434}"
      cd "$REPO_ROOT"
      return
    fi
    printf "."
    sleep 1
  done
  echo ""
  err "Ollama 启动超时。查看日志: docker-compose logs ollama"
  cd "$REPO_ROOT"
}

start_mcp() {
  echo ""
  echo "=== 启动 MCP Server (${AGENTS_MEMORY_ENV}) ==="
  if [[ -f "$MCP_PID_FILE" ]]; then
    local pid
    pid=$(cat "$MCP_PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      warn "MCP Server 已在运行 (PID $pid)。"
      return
    fi
    rm -f "$MCP_PID_FILE"
  fi

  env AGENTS_MEMORY_ENV="$AGENTS_MEMORY_ENV" AGENTS_MEMORY_ENV_FILE="$AGENTS_MEMORY_ENV_FILE" \
    OLLAMA_HOST="${OLLAMA_HOST:-}" OLLAMA_PORT="${OLLAMA_PORT:-}" QDRANT_HOST="${QDRANT_HOST:-}" \
    QDRANT_PORT="${QDRANT_PORT:-}" "$PYTHON" "$MCP_SERVER" &
  echo $! > "$MCP_PID_FILE"
  sleep 1

  local pid
  pid=$(cat "$MCP_PID_FILE")
  if kill -0 "$pid" 2>/dev/null; then
    ok "MCP Server: 后台运行 (PID $pid)"
  else
    err "MCP Server 启动失败。手动调试: $PYTHON $MCP_SERVER"
    rm -f "$MCP_PID_FILE"
  fi
}

start_mcp_debug() {
  echo ""
  echo "=== MCP Server 调试模式（前台，${AGENTS_MEMORY_ENV}）==="
  warn "以 stdio 模式运行，发送 JSON-RPC 请求测试。Ctrl-C 退出。"
  env AGENTS_MEMORY_ENV="$AGENTS_MEMORY_ENV" AGENTS_MEMORY_ENV_FILE="$AGENTS_MEMORY_ENV_FILE" \
    OLLAMA_HOST="${OLLAMA_HOST:-}" OLLAMA_PORT="${OLLAMA_PORT:-}" QDRANT_HOST="${QDRANT_HOST:-}" \
    QDRANT_PORT="${QDRANT_PORT:-}" "$PYTHON" "$MCP_SERVER"
}

show_status() {
  echo ""
  echo "=== Agents-Memory 服务状态 (${AGENTS_MEMORY_ENV}) ==="
  info "调试日志: $LOG_FILE"

  if curl -sf "http://localhost:${QDRANT_PORT:-6333}/readyz" &>/dev/null; then
    ok "Qdrant:     http://localhost:${QDRANT_PORT:-6333}  (running)"
  else
    warn "Qdrant:     未运行"
  fi

  if curl -sf "http://localhost:${OLLAMA_PORT:-11434}/api/tags" &>/dev/null; then
    ok "Ollama:     http://localhost:${OLLAMA_PORT:-11434}  (running)"
  else
    info "Ollama:     未运行"
  fi

  if [[ -f "$MCP_PID_FILE" ]] && kill -0 "$(cat "$MCP_PID_FILE")" 2>/dev/null; then
    ok "MCP Server: 后台运行 (PID $(cat "$MCP_PID_FILE"))"
  else
    info "MCP Server: 未运行"
  fi

  ok "Python:     $($PYTHON --version)"
  if $PYTHON -c "from mcp.server.fastmcp import FastMCP" 2>/dev/null; then
    ok "mcp pkg:    installed"
  else
    warn "mcp pkg:    未安装"
  fi

  echo ""
  echo "=== 记忆库状态 ==="
  $PYTHON "$REPO_ROOT/scripts/memory.py" stats 2>/dev/null || true
}

stop_services() {
  echo ""
  echo "=== 停止服务 (${AGENTS_MEMORY_ENV}) ==="

  if [[ -f "$MCP_PID_FILE" ]]; then
    local pid
    pid=$(cat "$MCP_PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" && rm -f "$MCP_PID_FILE"
      ok "MCP Server 已停止 (PID $pid)"
    fi
  fi

  if curl -sf "http://localhost:${QDRANT_PORT:-6333}/readyz" &>/dev/null; then
    cd "$DOCKER_DIR"
    QDRANT_PORT="${QDRANT_PORT:-6333}" QDRANT_GRPC_PORT="${QDRANT_GRPC_PORT:-6334}" compose stop qdrant
    cd "$REPO_ROOT"
    ok "Qdrant 已停止。"
  else
    info "Qdrant 未在运行。"
  fi

  if curl -sf "http://localhost:${OLLAMA_PORT:-11434}/api/tags" &>/dev/null; then
    cd "$DOCKER_DIR"
    OLLAMA_PORT="${OLLAMA_PORT:-11434}" compose stop ollama
    cd "$REPO_ROOT"
    ok "Ollama 已停止。"
  else
    info "Ollama 未在运行。"
  fi
}

cmd_config() {
  if [[ "$PRINT_JSON" == "true" ]]; then
    agents_memory_print_env_json
    return
  fi
  echo ""
  echo "=== Runtime Config (${AGENTS_MEMORY_ENV}) ==="
  echo "env file         : $AGENTS_MEMORY_ENV_FILE"
  echo "mcp pid file     : $MCP_PID_FILE"
  echo "runtime log      : $LOG_FILE"
  echo "qdrant host/port : ${QDRANT_HOST:-localhost}:${QDRANT_PORT:-6333}"
  echo "ollama host/port : ${OLLAMA_HOST:-http://localhost:${OLLAMA_PORT:-11434}}"
}

DOCKER_OK=false
CMD="${1:-all}"

case "$CMD" in
  all)
    check_deps
    start_qdrant
    show_status
    ;;
  --qdrant|qdrant)
    check_deps
    start_qdrant
    ;;
  --ollama|ollama)
    check_deps
    start_ollama
    ;;
  --with-ollama|with-ollama)
    check_deps
    start_qdrant
    start_ollama
    show_status
    ;;
  --mcp|mcp)
    check_deps
    start_mcp_debug
    ;;
  mcp-bg)
    check_deps
    start_mcp
    ;;
  stop)
    stop_services
    ;;
  restart)
    stop_services
    sleep 1
    check_deps
    start_qdrant
    if [[ "${START_OLLAMA_ON_RESTART:-false}" == "true" ]]; then
      start_ollama
    fi
    show_status
    ;;
  status)
    show_status
    ;;
  config)
    cmd_config
    ;;
  *)
    echo "用法: bash scripts/runtime/manage.sh [--env local|staging|prod] [all|status|stop|restart|qdrant|ollama|with-ollama|mcp|mcp-bg|config] [--json]"
    exit 1
    ;;
esac
