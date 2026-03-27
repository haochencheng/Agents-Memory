from __future__ import annotations

DEFAULT_BRIDGE_INSTRUCTION_REL = ".github/instructions/agents-memory-bridge.instructions.md"
COPILOT_INSTRUCTIONS_REL = ".github/copilot-instructions.md"
AGENTS_ROUTER_REL = "AGENTS.md"
AGENTS_BLOCK_START = "<!-- agents-memory:read-order:start -->"
AGENTS_BLOCK_END = "<!-- agents-memory:read-order:end -->"
COPILOT_TEMPLATE_NAME = "agents-memory-copilot-instructions.md"
BRIDGE_TEMPLATE_NAME = "agents-memory-bridge.instructions.md"
COPILOT_BLOCK_START = "<!-- agents-memory:start -->"
COPILOT_BLOCK_END = "<!-- agents-memory:end -->"
VSCODE_DIRNAME = ".vscode"
MCP_CONFIG_NAME = "mcp.json"
PYTHON_BIN = "python3.12"

VECTOR_THRESHOLD = 200
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
QDRANT_HOST_ENV = "QDRANT_HOST"
QDRANT_PORT_ENV = "QDRANT_PORT"
QDRANT_COLLECTION_ENV = "QDRANT_COLLECTION"
DEFAULT_QDRANT_HOST = "localhost"
DEFAULT_QDRANT_PORT = 6333
DEFAULT_QDRANT_COLLECTION = "agents-memory"

CATEGORIES = [
    "type-error", "logic-error", "finance-safety", "arch-violation",
    "test-failure", "docs-drift", "config-error", "build-error",
    "runtime-error", "security",
]

PROJECTS = [
    "synapse-network", "spec2flow", "provider-service",
    "gateway", "admin-front", "gateway-admin", "other",
]

DOMAINS = ["finance", "frontend", "python", "docs", "config", "infra", "other"]

DOMAIN_HINTS: list[tuple[str, str]] = [
    ("finance-backend", "finance"),
    ("finance-admin", "finance"),
    ("finance", "finance"),
    ("python", "python"),
    ("frontend", "frontend"),
    ("admin-console", "frontend"),
    ("docs", "docs"),
    ("config", "config"),
    ("infra", "infra"),
    ("safety", "config"),
]

REGISTER_HINT = "先运行: amem register"

