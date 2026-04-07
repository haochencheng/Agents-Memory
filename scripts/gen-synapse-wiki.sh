#!/usr/bin/env bash
# scripts/gen-synapse-wiki.sh — 为 Synapse-Network 批量生成 wiki 知识库
#
# 用法:
#   bash scripts/gen-synapse-wiki.sh           # 全量生成
#   bash scripts/gen-synapse-wiki.sh --dry-run # 预览模式
#   bash scripts/gen-synapse-wiki.sh --quick   # 只 wiki-ingest，跳过 LLM compile
#
# 前提:
#   - AGENTS_MEMORY_ROOT 已设置（或使用默认路径）
#   - Ollama 已运行（快速模式可跳过）
#   - AMEM_LLM_PROVIDER/MODEL 已配置

set -euo pipefail

AMEM_ROOT="${AGENTS_MEMORY_ROOT:-/Users/cliff/workspace/agent/Agents-Memory}"
SYNAPSE_ROOT="/Users/cliff/workspace/agent/Synapse-Network"
AMEM="python3.12 ${AMEM_ROOT}/scripts/amem"

# 确保 amem 可以找到 Agents-Memory
export AGENTS_MEMORY_ROOT="$AMEM_ROOT"
export AMEM_EMBED_PROVIDER="${AMEM_EMBED_PROVIDER:-ollama}"
export AMEM_LLM_PROVIDER="${AMEM_LLM_PROVIDER:-ollama}"
export AMEM_LLM_MODEL="${AMEM_LLM_MODEL:-qwen2.5:7b}"
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

# ─── 参数 ─────────────────────────────────────────────────────────────────────
DRY_RUN=false
QUICK=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --quick)   QUICK=true;   shift ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

# ─── 颜色 ─────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()      { echo -e "${GREEN}  ✅ $*${NC}"; }
warn()    { echo -e "${YELLOW}  ⚠️  $*${NC}"; }
err()     { echo -e "${RED}  ❌ $*${NC}"; }
info()    { echo -e "${BLUE}  ℹ  $*${NC}"; }
section() { echo -e "\n${BLUE}═══ $* ═══${NC}"; }

INGEST_OPTS=""
$DRY_RUN && INGEST_OPTS="--dry-run"

section "Synapse-Network Wiki 生成"
info "AMEM_ROOT:   $AMEM_ROOT"
info "SYNAPSE:     $SYNAPSE_ROOT"
info "DRY_RUN:     $DRY_RUN"
info "QUICK:       $QUICK"
info "LLM:         $AMEM_LLM_PROVIDER / $AMEM_LLM_MODEL"

# ─── 检查 amem 可用 ───────────────────────────────────────────────────────────
section "前置检查"
if ! python3.12 "${AMEM_ROOT}/scripts/amem" wiki-list &>/dev/null; then
  err "amem 不可用。检查 AGENTS_MEMORY_ROOT: $AMEM_ROOT"
  exit 1
fi
ok "amem 可用"

if ! $QUICK && ! curl -sf "${OLLAMA_HOST}/api/tags" &>/dev/null; then
  err "Ollama 未运行（${OLLAMA_HOST}）。运行: ollama serve"
  info "使用 --quick 跳过 LLM 步骤"
  exit 1
fi
$QUICK || ok "Ollama 在线"

# ─── wiki-ingest 文档 ────────────────────────────────────────────────────────

ingest_file() {
  local file="$1"
  local topic="$2"
  if $DRY_RUN; then
    info "[dry-run] wiki-ingest $file → topic=$topic"
    return
  fi
  if $AMEM wiki-ingest "$file" --topic "$topic" 2>&1; then
    ok "wiki-ingest: $topic"
  else
    warn "wiki-ingest 失败: $file"
  fi
}

section "1. 导入架构文档"
ingest_file "$SYNAPSE_ROOT/docs/ARCHITECTURE.md"    "synapse-architecture"
ingest_file "$SYNAPSE_ROOT/docs/README.md"           "synapse-overview"

section "2. 导入 Ops 文档"
for f in "$SYNAPSE_ROOT/docs/ops/"*.md; do
  [[ -f "$f" ]] || continue
  basename=$(basename "$f" .md)
  # 将序号前缀标准化为 topic 名：01_Local → synapse-ops-local
  topic="synapse-ops-$(echo "$basename" | sed 's/^[0-9]*_//' | tr '[:upper:]_' '[:lower:]-')"
  ingest_file "$f" "$topic"
done

section "3. 导入 Bugfix 记录"

# 顶层 bugfix 文件
for f in "$SYNAPSE_ROOT/docs/reference/bugfix/gateway/"*.md; do
  [[ -f "$f" ]] || continue
  basename=$(basename "$f" .md)
  topic="synapse-bugfix-$(echo "$basename" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/-$//')"
  ingest_file "$f" "$topic"
done

# 子目录 bugs.md 文件（每个子目录对应一个 wiki topic）
for subdir in "$SYNAPSE_ROOT/docs/reference/bugfix/gateway"/*/; do
  f="${subdir}bugs.md"
  [[ -f "$f" ]] || continue
  area=$(basename "$subdir")
  topic="synapse-${area}"
  ingest_file "$f" "$topic"
done

# scripts 目录
for f in "$SYNAPSE_ROOT/docs/reference/bugfix/scripts/"*.md; do
  [[ -f "$f" ]] || continue
  basename=$(basename "$f" .md)
  topic="synapse-scripts-$(echo "$basename" | tr '[:upper:]_' '[:lower:]-')"
  ingest_file "$f" "$topic"
done

section "4. 导入 Reference 文档"
for f in "$SYNAPSE_ROOT/docs/reference/"*.md; do
  [[ -f "$f" ]] || continue
  basename=$(basename "$f" .md)
  topic="synapse-ref-$(echo "$basename" | tr '[:upper:]_' '[:lower:]-' | sed 's/--*/-/g')"
  ingest_file "$f" "$topic"
done

# ─── wiki-compile（LLM 提炼）──────────────────────────────────────────────────
if $QUICK; then
  section "5. 跳过 wiki-compile（--quick 模式）"
  warn "使用 wiki-ingest 导入的是原始文档，未经 LLM 提炼。"
  info "后续运行: bash scripts/gen-synapse-wiki.sh 完成提炼。"
else
  section "5. LLM 提炼核心 Topics（wiki-compile）"
  COMPILE_TOPICS=(
    "synapse-architecture"
    "synapse-overview"
    "synapse-bugfix-bug-deposit-01-intent-status-false-failed"
    "synapse-billing"
    "synapse-discovery"
    "synapse-settlement"
  )
  for topic in "${COMPILE_TOPICS[@]}"; do
    # 检查 topic 页面是否存在
    if python3.12 "${AMEM_ROOT}/scripts/amem" wiki-list 2>/dev/null | grep -q "$topic"; then
      info "wiki-compile: $topic ..."
      if $DRY_RUN; then
        info "[dry-run] wiki-compile $topic --dry-run"
      else
        $AMEM wiki-compile "$topic" --provider ollama --model "$AMEM_LLM_MODEL" 2>&1 && ok "wiki-compile: $topic" || warn "wiki-compile 失败: $topic"
      fi
    else
      warn "跳过 wiki-compile（topic 未找到）: $topic"
    fi
  done
fi

# ─── wiki-lint ────────────────────────────────────────────────────────────────
section "6. Wiki 健康检查"
if $DRY_RUN; then
  info "[dry-run] 跳过 wiki-lint"
else
  $AMEM wiki-lint 2>&1 && ok "wiki-lint 通过" || warn "wiki-lint 发现问题（见上方输出）"
fi

# ─── 汇总 ────────────────────────────────────────────────────────────────────
section "完成"
if $DRY_RUN; then
  info "dry-run 模式，未写入任何文件。去掉 --dry-run 正式执行。"
else
  TOPIC_COUNT=$($AMEM wiki-list 2>/dev/null | grep -c "•" || echo "0")
  ok "Wiki 知识库已生成，共 $TOPIC_COUNT 个 topics"
  info "查询: python3.12 ${AMEM_ROOT}/scripts/amem wiki-query <关键词>"
  info "测试: python3.12 ${AMEM_ROOT}/scripts/test-synapse-wiki.py"
fi
