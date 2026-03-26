"""
agents_memory.cli — `amem` 命令的真实入口。

安装方式（任选其一）：

  # 方式 A：本地开发安装（修改即生效，推荐）
  pip install -e /Users/cliff/workspace/Agents-Memory

  # 方式 B：从 GitHub 直接安装（其他机器 / CI）
  pip install git+https://github.com/haochencheng/Agents-Memory.git

安装后全局可用：
  amem register
  amem bridge-install synapse-network
  amem list
  amem sync
  ...
"""

import os
import sys
import importlib.util
from pathlib import Path


def _find_repo_root() -> Path:
    """
    定位 Agents-Memory 仓库根目录，按优先级：
    1. AGENTS_MEMORY_ROOT 环境变量（手动覆盖）
    2. 本文件所在包的上两级（pip install -e 或 git+ 安装时）
    """
    env_root = os.environ.get("AGENTS_MEMORY_ROOT")
    if env_root:
        root = Path(env_root)
        if (root / "scripts" / "memory.py").exists():
            return root

    # 本文件路径: .../Agents-Memory/agents_memory/cli.py
    # 上两级:    .../Agents-Memory/
    candidate = Path(__file__).parent.parent
    if (candidate / "scripts" / "memory.py").exists():
        return candidate

    print(
        "❌ 无法定位 Agents-Memory 仓库。\n"
        "   请设置环境变量：export AGENTS_MEMORY_ROOT=/path/to/Agents-Memory",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> None:
    """amem CLI 入口 — 代理所有参数到 scripts/memory.py。"""
    repo_root = _find_repo_root()

    # 告知 memory.py 仓库根目录（覆盖 Path(__file__).parent.parent 的默认行为）
    os.environ["AGENTS_MEMORY_ROOT"] = str(repo_root)

    memory_py = repo_root / "scripts" / "memory.py"
    spec = importlib.util.spec_from_file_location("memory", memory_py)
    if spec is None or spec.loader is None:
        print(f"❌ 无法加载 {memory_py}", file=sys.stderr)
        sys.exit(1)

    mod = importlib.util.module_from_spec(spec)
    # 让 memory.py 里的 __file__ 仍然正确解析
    mod.__file__ = str(memory_py)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.main()
