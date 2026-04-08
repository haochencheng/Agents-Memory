#!/usr/bin/env bash
# scripts/start.sh — Agents-Memory 一键启动脚本
#
# 用法:
#   bash scripts/start.sh               # 检查依赖 + 启动 Qdrant + 打印验证提示
#   bash scripts/start.sh --mcp         # 只启动 MCP Server（前台，用于调试）
#   bash scripts/start.sh --qdrant      # 只启动 Qdrant
#   bash scripts/start.sh --ollama      # 只启动 Ollama
#   bash scripts/start.sh --with-ollama # 启动 Qdrant + Ollama
#   bash scripts/start.sh status   # 检查所有服务状态
#   bash scripts/start.sh stop     # 停止 Qdrant（MCP Server 由 VS Code 管理）
#
# 依赖:
#   python3.12  — MCP Server
#   docker-compose — Qdrant 向量数据库（可选，< 200 条记录时不需要）

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="python3.12"
MCP_SERVER="$REPO_ROOT/scripts/mcp_server.py"
DOCKER_DIR="$REPO_ROOT/docker"
MCP_PID_FILE="$REPO_ROOT/.mcp_server.pid"
LOG_FILE="$REPO_ROOT/logs/agents-memory.log"

compose() {
  docker-compose "$@"
}

# ─── 颜色 ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { printf "%b\n" "${GREEN}✅  $*${NC}"; }
warn() { printf "%b\n" "${YELLOW}⚠️   $*${NC}"; }
err()  { printf "%b\n" "${RED}❌  $*${NC}"; }
info() { printf "    %s\n" "$*"; }

# ─── 检查依赖 ─────────────────────────────────────────────────────────────────
check_deps() {
  echo ""
  echo "=== 依赖检查 ==="

  # Python 3.12
  if command -v "$PYTHON" &>/dev/null; then
    ok "Python: $($PYTHON --version)"
  else
    err "Python 3.12 未找到。安装: brew install python@3.12"
    exit 1
  fi

  # mcp 包
  if $PYTHON -c "from mcp.server.fastmcp import FastMCP" 2>/dev/null; then
    ok "mcp package: installed"
  else
    warn "mcp 未安装，正在安装..."
    $PYTHON -m pip install mcp --break-system-packages -q
    ok "mcp package: installed"
  fi

  # Docker（可选）
  if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    ok "Docker: $(docker --version | head -1)"
    DOCKER_OK=true
  else
    warn "Docker 未运行（Qdrant 不可用）。向量搜索将使用本地 LanceDB。"
    DOCKER_OK=false
  fi
}

# ─── 启动 Qdrant ──────────────────────────────────────────────────────────────
start_qdrant() {
  echo ""
  echo "=== 启动 Qdrant ==="
  if [[ "$DOCKER_OK" != "true" ]]; then
    warn "Docker 未就绪，跳过 Qdrant。"
    return
  fi

  mkdir -p "$DOCKER_DIR/data/qdrant"
  cd "$DOCKER_DIR"
  compose up -d qdrant

  # 等待健康检查
  printf "    等待 Qdrant 就绪"
  for i in $(seq 1 30); do
    if curl -sf http://localhost:6333/readyz &>/dev/null; then
      echo ""
      ok "Qdrant: http://localhost:6333  (Dashboard: http://localhost:6333/dashboard)"
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

# ─── 启动 Ollama ──────────────────────────────────────────────────────────────
start_ollama() {
  echo ""
  echo "=== 启动 Ollama ==="
  if [[ "$DOCKER_OK" != "true" ]]; then
    warn "Docker 未就绪，跳过 Ollama。"
    return
  fi

  mkdir -p "$DOCKER_DIR/data/ollama"
  cd "$DOCKER_DIR"
  compose up -d ollama

  printf "    等待 Ollama 就绪"
  for i in $(seq 1 45); do
    if curl -sf http://localhost:11434/api/tags &>/dev/null; then
      echo ""
      ok "Ollama: http://localhost:11434"
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

# ─── 启动 MCP Server（后台）──────────────────────────────────────────────────
start_mcp() {
  echo ""
  echo "=== 启动 MCP Server ==="

  # VS Code 会自动拉起 MCP Server，这里启动一个后台进程用于非 VS Code 环境
  if [[ -f "$MCP_PID_FILE" ]]; then
    pid=$(cat "$MCP_PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      warn "MCP Server 已在运行 (PID $pid)。"
      return
    fi
    rm -f "$MCP_PID_FILE"
  fi

  $PYTHON "$MCP_SERVER" &
  echo $! > "$MCP_PID_FILE"
  sleep 1

  pid=$(cat "$MCP_PID_FILE")
  if kill -0 "$pid" 2>/dev/null; then
    ok "MCP Server: 后台运行 (PID $pid)"
    info "VS Code 中无需手动启动 — .vscode/mcp.json 会自动管理。"
    info "停止: kill $(cat "$MCP_PID_FILE")"
  else
    err "MCP Server 启动失败。手动调试: $PYTHON $MCP_SERVER"
    rm -f "$MCP_PID_FILE"
  fi
}

# ─── 调试模式：前台运行 MCP Server ───────────────────────────────────────────
start_mcp_debug() {
  echo ""
  echo "=== MCP Server 调试模式（前台）==="
  warn "以 stdio 模式运行，发送 JSON-RPC 请求测试。Ctrl-C 退出。"
  $PYTHON "$MCP_SERVER"
}

# ─── 状态检查 ─────────────────────────────────────────────────────────────────
show_status() {
  echo ""
  echo "=== Agents-Memory 服务状态 ==="
  info "调试日志: $LOG_FILE"

  # Qdrant
  if curl -sf http://localhost:6333/readyz &>/dev/null; then
    ok "Qdrant:     http://localhost:6333  (running)"
  else
    warn "Qdrant:     未运行。启动: cd docker && docker-compose up -d"
  fi

  if curl -sf http://localhost:11434/api/tags &>/dev/null; then
    ok "Ollama:     http://localhost:11434  (running)"
  else
    info "Ollama:     未运行。启动: bash scripts/start.sh --ollama"
  fi

  # MCP Server
  if [[ -f "$MCP_PID_FILE" ]] && kill -0 "$(cat "$MCP_PID_FILE")" 2>/dev/null; then
    ok "MCP Server: 后台运行 (PID $(cat "$MCP_PID_FILE"))"
  else
    info "MCP Server: 由 VS Code 按需启动（.vscode/mcp.json 配置）"
  fi

  # Python 环境
  ok "Python:     $($PYTHON --version)"
  if $PYTHON -c "from mcp.server.fastmcp import FastMCP" 2>/dev/null; then
    ok "mcp pkg:    installed"
  else
    warn "mcp pkg:    未安装。运行: $PYTHON -m pip install mcp --break-system-packages"
  fi

  # 记录统计
  echo ""
  echo "=== 记忆库状态 ==="
  $PYTHON "$REPO_ROOT/scripts/memory.py" stats 2>/dev/null || true
}

# ─── 停止服务 ──────────────────────────────────────────────────────────────────
stop_services() {
  echo ""
  echo "=== 停止服务 ==="

  # MCP Server
  if [[ -f "$MCP_PID_FILE" ]]; then
    pid=$(cat "$MCP_PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" && rm -f "$MCP_PID_FILE"
      ok "MCP Server 已停止 (PID $pid)"
    fi
  fi

  # Qdrant
  if curl -sf http://localhost:6333/readyz &>/dev/null; then
    cd "$DOCKER_DIR" && compose stop qdrant && cd "$REPO_ROOT"
    ok "Qdrant 已停止。"
  else
    info "Qdrant 未在运行。"
  fi

  if curl -sf http://localhost:11434/api/tags &>/dev/null; then
    cd "$DOCKER_DIR" && compose stop ollama && cd "$REPO_ROOT"
    ok "Ollama 已停止。"
  else
    info "Ollama 未在运行。"
  fi
}

# ─── 打印 VS Code 验证提示 ────────────────────────────────────────────────────
print_vscode_tip() {
  echo ""
  echo "=== VS Code 验证 ==="
  info "调试日志: $LOG_FILE"
  info "在 VS Code Agent/Chat 面板中输入以下内容，验证 MCP 工具是否可用："
  echo ""
  echo '    请调用 memory_get_index 工具，告诉我当前有多少条错误记录。'
  echo ""
  info "如果工具调用成功，返回 index.md 内容，说明 MCP 集成完整。"
  info "如果提示找不到工具，检查 .vscode/mcp.json 路径是否正确。"
  echo ""
}

# ─── 主逻辑 ───────────────────────────────────────────────────────────────────
DOCKER_OK=false

case "${1:-all}" in
  all)
    check_deps
    start_qdrant
    print_vscode_tip
    show_status
    ;;
  --qdrant)
    check_deps
    start_qdrant
    ;;
  --ollama)
    check_deps
    start_ollama
    ;;
  --with-ollama)
    check_deps
    start_qdrant
    start_ollama
    print_vscode_tip
    show_status
    ;;
  --mcp)
    check_deps
    start_mcp_debug
    ;;
  status)
    DOCKER_OK=true
    show_status
    ;;
  stop)
    stop_services
    ;;
  *)
    echo "用法: bash scripts/start.sh [all|--qdrant|--ollama|--with-ollama|--mcp|status|stop]"
    exit 1
    ;;
esac
