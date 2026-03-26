from __future__ import annotations

import re
from pathlib import Path

from agents_memory.constants import COPILOT_BLOCK_END, COPILOT_BLOCK_START, COPILOT_INSTRUCTIONS_REL, COPILOT_TEMPLATE_NAME
from agents_memory.integrations.agents.base import AgentAdapter, AgentSetupResult
from agents_memory.logging_utils import log_file_update
from agents_memory.runtime import AppContext


class GitHubCopilotAdapter(AgentAdapter):
    name = "github-copilot"
    display_name = "GitHub Copilot"

    def _template_path(self, ctx: AppContext) -> Path:
        return ctx.templates_dir / COPILOT_TEMPLATE_NAME

    def render_block(self, ctx: AppContext, project_id: str) -> str:
        template_path = self._template_path(ctx)
        if not template_path.exists():
            raise FileNotFoundError(f"Copilot template not found: {template_path}")
        content = template_path.read_text(encoding="utf-8")
        return content.replace("{{PROJECT_ID}}", project_id).replace("{{AGENTS_MEMORY_ROOT}}", str(ctx.base_dir))

    def install(self, ctx: AppContext, project_root: Path, project_id: str) -> AgentSetupResult:
        instructions_file = project_root / COPILOT_INSTRUCTIONS_REL
        block = self.render_block(ctx, project_id).rstrip() + "\n"
        instructions_file.parent.mkdir(parents=True, exist_ok=True)

        if not instructions_file.exists():
            instructions_file.write_text(block, encoding="utf-8")
            log_file_update(ctx.logger, action="write_copilot_instructions", path=instructions_file, detail=f"project_id={project_id}")
            return AgentSetupResult(status="created", message=f"已写入 {instructions_file}")

        content = instructions_file.read_text(encoding="utf-8")
        if COPILOT_BLOCK_START in content and COPILOT_BLOCK_END in content:
            pattern = re.compile(rf"{re.escape(COPILOT_BLOCK_START)}.*?{re.escape(COPILOT_BLOCK_END)}\\n?", re.DOTALL)
            updated = pattern.sub(block, content, count=1)
            if updated != content:
                instructions_file.write_text(updated, encoding="utf-8")
                log_file_update(ctx.logger, action="update_copilot_instructions", path=instructions_file, detail=f"project_id={project_id}")
                return AgentSetupResult(status="updated", message=f"已更新 {instructions_file} 中的 Agents-Memory 激活块")
            return AgentSetupResult(status="unchanged", message=f"{instructions_file} 已包含最新的 Agents-Memory 激活块")

        merged = content.rstrip() + ("\n\n" if content.strip() else "") + block
        instructions_file.write_text(merged, encoding="utf-8")
        log_file_update(ctx.logger, action="merge_copilot_instructions", path=instructions_file, detail=f"project_id={project_id}")
        return AgentSetupResult(status="merged", message=f"已追加 Agents-Memory 激活块 → {instructions_file}")

    def doctor(self, ctx: AppContext, project_root: Path, project_id: str) -> tuple[str, str, str]:
        instructions_file = project_root / COPILOT_INSTRUCTIONS_REL
        if not instructions_file.exists():
            return "WARN", "copilot_activation", f"missing {instructions_file} (recommended for repo-wide auto-activation)"
        content = instructions_file.read_text(encoding="utf-8")
        if COPILOT_BLOCK_START in content and COPILOT_BLOCK_END in content:
            return "OK", "copilot_activation", f"Agents-Memory activation block present -> {instructions_file}"
        return "WARN", "copilot_activation", f"{instructions_file} exists but Agents-Memory activation block is missing"
