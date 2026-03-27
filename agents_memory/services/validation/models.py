from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationFinding:
    status: str
    key: str
    detail: str


@dataclass(frozen=True)
class DocumentMetadata:
    created_at: str
    updated_at: str
    doc_status: str


@dataclass(frozen=True)
class DocsTouchResult:
    target: str
    updated_at: str
    updated_files: list[str]
    skipped_files: list[str]
    dry_run: bool


@dataclass(frozen=True)
class RefactorHotspot:
    status: str
    relative_path: str
    function_name: str
    qualified_name: str
    line: int
    effective_lines: int
    branches: int
    nesting: int
    local_vars: int
    has_guiding_comment: bool
    issues: list[str]
    score: int

    @property
    def identifier(self) -> str:
        return f"{self.relative_path}::{self.qualified_name}"

    @property
    def rank_token(self) -> str:
        digest = hashlib.sha1(self.identifier.encode("utf-8")).hexdigest()[:12]
        return f"hotspot-{digest}"

    @property
    def summary(self) -> str:
        label = "high complexity" if self.status == "WARN" else "approaching refactor threshold"
        return f"{self.identifier} {label} ({', '.join(self.issues)})"