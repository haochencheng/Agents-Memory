from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from agents_memory.runtime import AppContext


@dataclass(frozen=True)
class AgentSetupResult:
    status: str
    message: str


class AgentAdapter(ABC):
    name: str
    display_name: str
    supported: bool = True

    @abstractmethod
    def install(self, ctx: AppContext, project_root: Path, project_id: str) -> AgentSetupResult:
        raise NotImplementedError

    @abstractmethod
    def doctor(self, ctx: AppContext, project_root: Path, project_id: str) -> tuple[str, str, str] | None:
        raise NotImplementedError
