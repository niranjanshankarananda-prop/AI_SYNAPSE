"""
AI_SYNAPSE — Core Package

Contains core functionality: router, CARL, memory, skills, agent loop.
"""

from .config import (
    ConfigManager,
    SynapseConfig,
    get_config_manager,
    get_config,
)

from .agent_response import (
    AgentResponse,
    ResponseType,
    ToolCall,
    ToolResult,
)

from .agent_loop import AgentLoop

__all__ = [
    "ConfigManager",
    "SynapseConfig",
    "get_config_manager",
    "get_config",
    "AgentResponse",
    "ResponseType",
    "ToolCall",
    "ToolResult",
    "AgentLoop",
]
