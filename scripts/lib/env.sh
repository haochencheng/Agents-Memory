#!/usr/bin/env bash
# Shared environment loading for categorized startup scripts.

set -euo pipefail

agents_memory_load_env() {
  local repo_root="$1"
  local env_name="${2:-${AGENTS_MEMORY_ENV:-local}}"
  local env_file="${AGENTS_MEMORY_ENV_FILE:-$repo_root/config/environments/${env_name}.env}"

  if [[ ! -f "$env_file" ]]; then
    echo "Agents-Memory env file not found: $env_file" >&2
    return 1
  fi

  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a

  export AGENTS_MEMORY_ENV="${AGENTS_MEMORY_ENV:-$env_name}"
  export AGENTS_MEMORY_ENV_FILE="$env_file"
}

agents_memory_print_env_json() {
  cat <<EOF
{"environment":"${AGENTS_MEMORY_ENV}","env_file":"${AGENTS_MEMORY_ENV_FILE}","api_host":"${AGENTS_MEMORY_API_HOST:-}","api_port":"${AGENTS_MEMORY_API_PORT:-}","ui_host":"${AGENTS_MEMORY_UI_HOST:-}","ui_port":"${AGENTS_MEMORY_UI_PORT:-}","api_proxy_target":"${AGENTS_MEMORY_API_PROXY_TARGET:-}","qdrant_host":"${QDRANT_HOST:-}","qdrant_port":"${QDRANT_PORT:-}","qdrant_grpc_port":"${QDRANT_GRPC_PORT:-}","ollama_host":"${OLLAMA_HOST:-}","ollama_port":"${OLLAMA_PORT:-}"}
EOF
}
