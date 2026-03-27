from agents_memory.services.integration import (
    cmd_agent_list,
    cmd_agent_setup,
    cmd_bridge_install,
    cmd_copilot_setup,
    cmd_doctor,
    cmd_mcp_setup,
    cmd_register,
    cmd_sync,
)
from agents_memory.services.planning import cmd_plan_init
from agents_memory.services.profiles import cmd_profile_apply, cmd_profile_list, cmd_profile_render, cmd_profile_show, cmd_standards_sync
from agents_memory.services.projects import parse_projects, resolve_project_target
from agents_memory.services.records import (
    cmd_archive,
    cmd_list,
    cmd_new,
    cmd_promote,
    cmd_search,
    cmd_stats,
    cmd_update_index,
)
from agents_memory.services.validation import cmd_docs_check, cmd_plan_check, cmd_profile_check
from agents_memory.services.vector import cmd_embed, cmd_to_qdrant, cmd_vsearch
