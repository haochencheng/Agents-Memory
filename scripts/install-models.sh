#!/usr/bin/env bash
# scripts/install-models.sh — Agents-Memory 本地模型一键安装脚本
#
# 用途:
#   安装 Ollama，拉取 embedding 和 LLM 合成所需模型
#
# 用法:
#   bash scripts/install-models.sh                   # 默认安装（nomic-embed-text + qwen2.5:7b）
#   bash scripts/install-models.sh --preset fast     # 极速：nomic-embed-text + gemma4:e4b（更小更快）
#   bash scripts/install-models.sh --preset quality  # 质量优先：bge-m3 + qwen2.5:14b
#   bash scripts/install-models.sh --embed bge-m3 --llm gemma4:e4b  # 自定义
#   bash scripts/install-models.sh --status          # 仅检查状态
#
# 支持平台: macOS（Apple Silicon / Intel），Linux
# macOS 推荐通过 Homebrew 安装 Ollama（原生 Apple Silicon 支持，GPU 加速）
# Linux 推荐通过官方安装脚本

set -euo pipefail

# ─── 颜色 ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅  $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️   $*${NC}"; }
err()  { echo -e "${RED}❌  $*${NC}"; exit 1; }
info() { echo -e "${BLUE}    $*${NC}"; }
section() { echo -e "\n${BLUE}═══ $* ═══${NC}"; }

# ─── 默认配置 ─────────────────────────────────────────────────────────────────
EMBED_MODEL="nomic-embed-text"
LLM_MODEL="qwen2.5:7b"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

# ─── 参数解析 ─────────────────────────────────────────────────────────────────
STATUS_ONLY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --preset)
      case "$2" in
        fast)    EMBED_MODEL="nomic-embed-text"; LLM_MODEL="gemma4:e4b" ;;
        quality) EMBED_MODEL="bge-m3";           LLM_MODEL="qwen2.5:14b" ;;
        default) EMBED_MODEL="nomic-embed-text"; LLM_MODEL="qwen2.5:7b" ;;
        *)       err "未知 preset: $2（可选: default/fast/quality）" ;;
      esac
      shift 2 ;;
    --embed)   EMBED_MODEL="$2"; shift 2 ;;
    --llm)     LLM_MODEL="$2";   shift 2 ;;
    --status)  STATUS_ONLY=true; shift ;;
    -h|--help)
      echo "用法: bash scripts/install-models.sh [--preset default|fast|quality] [--embed MODEL] [--llm MODEL] [--status]"
      exit 0 ;;
    *) err "未知参数: $1" ;;
  esac
done

# ─── 检测操作系统 ──────────────────────────────────────────────────────────────
detect_os() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux)  echo "linux" ;;
    *)      echo "unknown" ;;
  esac
}

OS=$(detect_os)

section "Agents-Memory 本地模型安装"
info "目标 Embedding 模型: ${EMBED_MODEL}"
info "目标 LLM 合成模型:   ${LLM_MODEL}"
info "Ollama 服务地址:     ${OLLAMA_HOST}"

# ─── 安装 Ollama ───────────────────────────────────────────────────────────────
install_ollama() {
  section "安装 Ollama"

  if command -v ollama &>/dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>&1 | head -1)
    ok "Ollama 已安装: ${OLLAMA_VERSION}"
    return
  fi

  case "$OS" in
    macos)
      if command -v brew &>/dev/null; then
        info "通过 Homebrew 安装 Ollama（推荐，原生 Apple Silicon GPU 支持）..."
        brew install ollama
        ok "Ollama 已通过 Homebrew 安装"
      else
        info "Homebrew 未找到，通过官方脚本安装..."
        curl -fsSL https://ollama.com/install.sh | sh
        ok "Ollama 已安装"
      fi
      ;;
    linux)
      info "通过官方脚本安装 Ollama..."
      curl -fsSL https://ollama.com/install.sh | sh
      ok "Ollama 已安装"
      ;;
    *)
      err "不支持的操作系统: $(uname -s)。请手动安装 Ollama: https://ollama.com/download"
      ;;
  esac
}

# ─── 启动 Ollama 服务 ─────────────────────────────────────────────────────────
start_ollama_service() {
  section "启动 Ollama 服务"

  # 检查是否已运行
  if curl -sf "${OLLAMA_HOST}/api/tags" &>/dev/null; then
    ok "Ollama 服务已在运行: ${OLLAMA_HOST}"
    return
  fi

  case "$OS" in
    macos)
      if command -v brew &>/dev/null && brew services list 2>/dev/null | grep -q ollama; then
        info "通过 Homebrew 启动 Ollama 服务..."
        brew services start ollama
      else
        info "后台启动 Ollama 服务..."
        ollama serve &>/dev/null &
        disown
      fi
      ;;
    linux)
      if command -v systemctl &>/dev/null && systemctl list-units --type=service 2>/dev/null | grep -q ollama; then
        info "通过 systemctl 启动 Ollama..."
        sudo systemctl start ollama
      else
        info "后台启动 Ollama 服务..."
        ollama serve &>/dev/null &
        disown
      fi
      ;;
  esac

  # 等待服务就绪
  echo -n "    等待 Ollama 就绪"
  for i in $(seq 1 30); do
    if curl -sf "${OLLAMA_HOST}/api/tags" &>/dev/null; then
      echo ""
      ok "Ollama 服务: ${OLLAMA_HOST}"
      return
    fi
    echo -n "."
    sleep 1
  done
  echo ""
  err "Ollama 服务启动超时。请手动运行: ollama serve"
}

# ─── 拉取模型 ─────────────────────────────────────────────────────────────────
pull_model() {
  local model="$1"
  local label="$2"
  section "拉取 ${label}: ${model}"

  # 检查是否已有该模型
  if curl -sf "${OLLAMA_HOST}/api/tags" | python3 -c "
import sys, json
tags = json.load(sys.stdin)
models = [m['name'] for m in tags.get('models', [])]
base = '${model}'.split(':')[0]
tag = '${model}'.split(':')[1] if ':' in '${model}' else 'latest'
matched = any(m == '${model}' or m.startswith(base + ':') for m in models)
sys.exit(0 if matched else 1)
" 2>/dev/null; then
    ok "${model} 已就绪（跳过拉取）"
    return
  fi

  info "拉取 ${model}（首次安装，需要等待下载）..."
  ollama pull "${model}"
  ok "${model} 拉取完成"
}

# ─── 验证模型 ─────────────────────────────────────────────────────────────────
verify_models() {
  section "验证模型"

  # 验证 embedding
  info "测试 ${EMBED_MODEL} embedding..."
  EMBED_RESP=$(curl -sf "${OLLAMA_HOST}/api/embeddings" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${EMBED_MODEL}\",\"prompt\":\"test\"}" 2>&1)
  EMBED_LEN=$(echo "$EMBED_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('embedding',[])))" 2>/dev/null || echo "0")
  if [[ "$EMBED_LEN" -gt 0 ]]; then
    ok "Embedding 验证通过: ${EMBED_MODEL} → ${EMBED_LEN} 维向量"
  else
    warn "Embedding 验证失败: ${EMBED_MODEL}。响应: ${EMBED_RESP:0:200}"
  fi

  # 验证 LLM
  info "测试 ${LLM_MODEL} 生成..."
  LLM_RESP=$(curl -sf "${OLLAMA_HOST}/api/generate" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${LLM_MODEL}\",\"prompt\":\"回答: 1+1=?\",\"stream\":false}" 2>&1)
  LLM_OK=$(echo "$LLM_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok' if d.get('response') else 'fail')" 2>/dev/null || echo "fail")
  if [[ "$LLM_OK" == "ok" ]]; then
    ok "LLM 验证通过: ${LLM_MODEL}"
  else
    warn "LLM 验证失败: ${LLM_MODEL}。响应: ${LLM_RESP:0:200}"
  fi
}

# ─── 写 .env 配置 ──────────────────────────────────────────────────────────────
write_env_config() {
  section "更新环境变量配置"
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  ENV_FILE="$REPO_ROOT/.env.local"

  cat > "$ENV_FILE" << EOF
# Agents-Memory 本地模型配置（由 install-models.sh 自动生成）
# 生成时间: $(date -u +%Y-%m-%dT%H:%M:%SZ)

# Embedding 配置
AMEM_EMBED_PROVIDER=ollama
OLLAMA_HOST=${OLLAMA_HOST}

# LLM 合成配置
AMEM_LLM_PROVIDER=ollama
AMEM_LLM_MODEL=${LLM_MODEL}

# 模型信息（供参考）
# EMBED_MODEL: ${EMBED_MODEL}
# LLM_MODEL:   ${LLM_MODEL}
EOF
  ok "配置已写入: ${ENV_FILE}"
  info "使用方法: source ${ENV_FILE} && amem wiki-compile <topic>"
}

# ─── 状态检查 ─────────────────────────────────────────────────────────────────
show_status() {
  section "当前模型状态"
  if curl -sf "${OLLAMA_HOST}/api/tags" &>/dev/null; then
    ok "Ollama 服务: ${OLLAMA_HOST}"
    echo ""
    info "已安装模型:"
    curl -s "${OLLAMA_HOST}/api/tags" | python3 -c "
import sys, json
tags = json.load(sys.stdin)
for m in tags.get('models', []):
    size_gb = m.get('size', 0) / 1024**3
    print(f'  • {m[\"name\"]:40s} {size_gb:.1f} GB')
" 2>/dev/null || echo "  （无法解析模型列表）"
  else
    warn "Ollama 未运行。启动: ollama serve"
  fi
}

# ─── 输出使用提示 ─────────────────────────────────────────────────────────────
print_next_steps() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  安装完成！下一步："
  echo ""
  echo "  1. 激活配置:"
  echo "     source .env.local"
  echo ""
  echo "  2. 运行 E2E 测试:"
  echo "     bash scripts/test-ollama-chain.sh"
  echo ""
  echo "  3. 为 Synapse-Network 生成 Wiki:"
  echo "     bash scripts/gen-synapse-wiki.sh"
  echo ""
  echo "  4. 切换回 OpenAI（生产环境）:"
  echo "     export AMEM_EMBED_PROVIDER=openai"
  echo "     export AMEM_LLM_PROVIDER=anthropic"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ─── 主逻辑 ───────────────────────────────────────────────────────────────────
if $STATUS_ONLY; then
  show_status
  exit 0
fi

install_ollama
start_ollama_service
pull_model "$EMBED_MODEL" "Embedding 模型"
pull_model "$LLM_MODEL"   "LLM 合成模型"
verify_models
write_env_config
show_status
print_next_steps
