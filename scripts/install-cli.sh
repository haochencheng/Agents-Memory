#!/usr/bin/env bash
# scripts/install-cli.sh — 把 `amem` 命令安装到系统 PATH
#
# 用法（在任意目录执行，无需 cd 到 Agents-Memory）:
#   bash /path/to/Agents-Memory/scripts/install-cli.sh
#
# 效果:
#   /opt/homebrew/bin/amem -> /path/to/Agents-Memory/scripts/amem
#   在任意目录可直接使用 `amem register` / `amem bridge-install` 等命令
#
# 卸载:
#   rm /opt/homebrew/bin/amem

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AMEM_SCRIPT="$REPO_ROOT/scripts/amem"
GREEN='\033[0;32m'; NC='\033[0m'

# 确保脚本可执行
chmod +x "$AMEM_SCRIPT"

# 选择安装目录（优先 Homebrew，其次 /usr/local/bin）
if [[ -d /opt/homebrew/bin ]]; then
  INSTALL_DIR="/opt/homebrew/bin"
elif [[ -d /usr/local/bin ]]; then
  INSTALL_DIR="/usr/local/bin"
else
  INSTALL_DIR="$HOME/.local/bin"
  mkdir -p "$INSTALL_DIR"
fi

TARGET="$INSTALL_DIR/amem"

# 如果已存在，先删除旧链接
[[ -L "$TARGET" ]] && rm "$TARGET"
[[ -f "$TARGET" ]] && { echo "⚠️  $TARGET 已存在且非符号链接，请手动处理。"; exit 1; }

ln -sf "$AMEM_SCRIPT" "$TARGET"

echo -e "${GREEN}✅  amem 已安装 → $TARGET${NC}"
echo "    → $AMEM_SCRIPT"
echo ""
echo "验证:"
echo "  amem stats"
echo ""
echo "其他项目接入方式:"
echo "  cd /path/to/your-project"
echo "  amem register"
