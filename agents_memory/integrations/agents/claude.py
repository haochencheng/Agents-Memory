from __future__ import annotations

from pathlib import Path

from agents_memory.integrations.agents.base import AgentAdapter, AgentSetupResult
from agents_memory.runtime import AppContext


class ClaudeAdapter(AgentAdapter):
    name = "claude"
    display_name = "Claude"
    supported = False

    def install(self, ctx: AppContext, project_root: Path, project_id: str) -> AgentSetupResult:
        return AgentSetupResult(
            status="unsupported",
            message="Claude adapter scaffold is registered, but a stable repo-local installation flow is not implemented yet.",
        )

    def doctor(self, ctx: AppContext, project_root: Path, project_id: str):
        return None
