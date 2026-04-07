from __future__ import annotations

import sys
from collections.abc import Callable

from agents_memory.commands import integration as integration_commands
from agents_memory.commands import ingest as ingest_commands
from agents_memory.commands import planning as planning_commands
from agents_memory.commands import profiles as profile_commands
from agents_memory.commands import records as record_commands
from agents_memory.commands import search as search_commands
from agents_memory.commands import validation as validation_commands
from agents_memory.commands import vector as vector_commands
from agents_memory.commands import wiki as wiki_commands
from agents_memory.commands import workflows as workflow_commands
from agents_memory.runtime import build_context

USAGE = """Agents-Memory CLI — 错误记录管理工具

用法:
  python3 memory.py new                        # 交互式创建新错误记录
  python3 memory.py list                       # 列出所有 new/reviewed 状态的记录
  python3 memory.py stats                      # 统计各类别错误数量
  python3 memory.py search <keyword>           # 关键词搜索（< 200 条默认策略）
  python3 memory.py vsearch <query>            # 语义向量搜索（需先运行 embed）
  python3 memory.py embed                      # 构建 / 更新本地 LanceDB 向量索引
  python3 memory.py promote <id>               # 将错误记录升级为 instruction 规则
  python3 memory.py sync                       # 将已升级规则自动写入注册项目的 instruction 文件
  python3 memory.py bridge-install <project>   # 在注册项目中安装 bridge instruction
  python3 memory.py copilot-setup [project-id] # 安装 GitHub Copilot 仓库级激活块
  python3 memory.py agent-list                 # 查看内置 agent adapter 列表
  python3 memory.py agent-setup <agent> [path] # 为指定 agent 安装集成
  python3 memory.py register [path]            # 一键注册新项目（agent + bridge + mcp）
  python3 memory.py mcp-setup [project-id]     # 在已注册项目中写入 .vscode/mcp.json
    python3 memory.py enable [path] [--full] [--dry-run] [--json]
                                                                                             # 一键启用 Shared Engineering Brain；--full 会附加 profile、Copilot 和 refactor bundle，--dry-run 预览变更，--json 输出结构化预览
    python3 memory.py bootstrap [path] [--full] [--dry-run] [--json]
                                                                                                                                                                                         # 顶层 workflow 入口；语义等价于 enable，更适合按用户意图组织接入流程
  python3 memory.py doctor [project-id] [--write-checklist] [--write-state]
                                               # 检查项目是否已完整接入 Agents-Memory，并可导出 onboarding 工件
  python3 memory.py onboarding-execute [path] [--approve-unsafe]
                                               # 执行当前第一条 onboarding action；仅自动执行安全步骤，危险步骤需显式批准
  python3 memory.py plan-init <task> [path]    # 初始化 spec / plan / task-graph / validation bundle
    python3 memory.py start-task <task> [path]   # 顶层 workflow 入口；语义等价于 plan-init
    python3 memory.py do-next [path] [--format text|json]
                                                                                             # 输出当前 onboarding 下一步动作，避免 agent 自行猜测当前阻塞项
    python3 memory.py validate [path] [--strict] [--format text|json]
                                                                                             # 聚合 docs/profile/planning/doctor 成统一交付门
        python3 memory.py close-task [path] [--slug <task-slug>] [--strict] [--format text|json]
                                                                                                                                                                                                                                                                                                                                                                                 # 在 gate 通过后回写 planning bundle 与 onboarding state，完成任务事务闭环
  python3 memory.py onboarding-bundle [path]   # 从 onboarding-state.json 生成 onboarding task bundle
    python3 memory.py refactor-bundle [path] [--token <hotspot-token>] [--index <n>]
                                                                                             # 根据稳定 hotspot token 或当前排序位置生成 refactor task bundle
  python3 memory.py plan-check [path]          # 校验 docs/plans 下 planning bundle 的完整性
        python3 memory.py docs-touch [path] [--date YYYY-MM-DD] [--dry-run] [--format text|json]
                                                                                                                                                                                         # 自动刷新受管 Markdown 文档的 updated_at；缺失 front matter 时补齐元数据
    python3 memory.py profile-list               # 查看可用 profile 列表
    python3 memory.py profile-show <profile-id>  # 查看指定 profile 的装配内容
    python3 memory.py profile-apply <id> [path]  # 把 profile 安装到目标项目
    python3 memory.py profile-diff <id> [path]   # 预览 profile 将写入哪些内容
    python3 memory.py profile-render [path]      # 根据 project facts 重渲染 profile overlays
    python3 memory.py standards-sync [path]      # 同步 profile 管理的组织标准文件
    python3 memory.py profile-check [path]       # 校验已安装 profile 的一致性
    python3 memory.py docs-check [path]          # 校验文档入口、contract/test/policy 漂移与明显过期内容
  python3 memory.py archive                    # 归档 90 天以上且无重复的记录
  python3 memory.py update-index               # 重新生成 index.md 统计数字
  python3 memory.py to-qdrant                  # 迁移向量索引到 Qdrant（多 Agent 共享）
  python3 memory.py wiki-list                  # 列出所有 Wiki 主题
  python3 memory.py wiki-query <keyword>       # 关键词搜索 Wiki，输出相关摘要（可作为 prompt 前缀注入）
  python3 memory.py wiki-ingest <path>         # 将本地 Markdown 文档导入 Wiki
    [--topic <name>]                           # 指定主题名（默认使用文件名）
  python3 memory.py wiki-sync <topic>          # 写入或更新一个 Wiki 主题页
    [--content <text>]                         # 直接传入内容
    [--from-file <path>]                       # 从文件读取内容（或通过 stdin 传入）
"""


def command_registry() -> dict[str, Callable]:
    registry: dict[str, Callable] = {}
    registry.update(record_commands.register())
    registry.update(vector_commands.register())
    registry.update(integration_commands.register())
    registry.update(ingest_commands.register())
    registry.update(planning_commands.register())
    registry.update(search_commands.register())
    registry.update(profile_commands.register())
    registry.update(validation_commands.register())
    registry.update(workflow_commands.register())
    registry.update(wiki_commands.register())
    return registry


def _log_command_start(ctx, args: list[str]) -> None:
    command = args[0] if args else "list"
    ctx.logger.info("command_start | command=%s | argv=%s", command, args)


def _log_command_end(ctx, args: list[str], *, status: str) -> None:
    command = args[0] if args else "list"
    ctx.logger.info("command_end | command=%s | status=%s", command, status)


def main(argv: list[str] | None = None) -> None:
    ctx = build_context(reference_file=__file__)
    ctx.ensure_storage_dirs()
    args = list(sys.argv[1:] if argv is None else argv)
    _log_command_start(ctx, args)
    commands = command_registry()
    try:
        command_name = args[0] if args else "list"
        handler = commands.get(command_name)
        if handler is None:
            print(USAGE)
        else:
            handler(ctx, args[1:] if args else [])
        _log_command_end(ctx, args, status="ok")
    except Exception:
        _log_command_end(ctx, args, status="error")
        ctx.logger.exception("command_failed | argv=%s", args)
        raise
