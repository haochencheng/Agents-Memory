from __future__ import annotations

from agents_memory.integrations.agents.base import AgentAdapter
from agents_memory.integrations.agents.chatgpt import ChatGPTAdapter
from agents_memory.integrations.agents.claude import ClaudeAdapter
from agents_memory.integrations.agents.github_copilot import GitHubCopilotAdapter


DEFAULT_AGENT = "github-copilot"


def built_in_adapters() -> dict[str, AgentAdapter]:
    adapters: list[AgentAdapter] = [
        GitHubCopilotAdapter(),
        ChatGPTAdapter(),
        ClaudeAdapter(),
    ]
    return {adapter.name: adapter for adapter in adapters}


def get_agent_adapter(agent_name: str) -> AgentAdapter | None:
    return built_in_adapters().get(agent_name)


def list_agent_adapters() -> list[AgentAdapter]:
    return list(built_in_adapters().values())
