"""
AI_SYNAPSE — Agent Response Types

Unified response format for all providers, regardless of whether they use
native function calling or prompt-based tool parsing.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class ResponseType(Enum):
    """Type of agent response chunk."""
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"


@dataclass
class ToolCall:
    """A single tool call from the AI."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Result of executing a tool."""
    tool_call_id: str = ""
    name: str = ""
    output: str = ""
    is_error: bool = False


@dataclass
class AgentResponse:
    """
    Unified response from any provider.

    Can represent:
    - A text chunk (streaming or complete)
    - A tool call request from the AI
    - A tool result to send back
    - An error
    - A done signal
    """
    type: ResponseType
    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_result: Optional[ToolResult] = None
    finish_reason: Optional[str] = None  # "stop", "tool_calls", "length"
