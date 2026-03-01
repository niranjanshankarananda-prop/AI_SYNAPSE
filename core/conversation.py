"""
AI_SYNAPSE — Conversation Management

Manages conversation history, context window, and message formatting.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Single message in conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API calls."""
        d: Dict[str, Any] = {
            "role": self.role,
            "content": self.content
        }
        # Tool call results need tool_call_id
        if self.role == "tool" and self.metadata:
            if "tool_call_id" in self.metadata:
                d["tool_call_id"] = self.metadata["tool_call_id"]
            if "name" in self.metadata:
                d["name"] = self.metadata["name"]
        # Assistant messages with tool calls
        if self.role == "assistant" and self.metadata and "tool_calls" in self.metadata:
            d["tool_calls"] = self.metadata["tool_calls"]
            if not self.content:
                d["content"] = None
        return d


class Conversation:
    """
    Manages conversation state and context window.
    
    Tracks:
    - Message history
    - Token usage estimation
    - Context bracket status
    - Session persistence
    
    Example:
        conv = Conversation(max_tokens=128000)
        conv.add_message("user", "Hello")
        conv.add_message("assistant", "Hi there!")
        
        # Check context usage
        usage = conv.get_context_usage()
        if usage > 0.75:
            conv.compact()  # Summarize old messages
    """
    
    # Rough token estimation (4 chars per token on average)
    CHARS_PER_TOKEN = 4
    
    def __init__(
        self,
        max_tokens: int = 128000,
        system_prompt: str = "",
        session_id: Optional[str] = None
    ):
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.messages: List[Message] = []
        self.total_tokens = 0
        self.system_tokens = self._estimate_tokens(system_prompt)
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation."""
        return len(text) // self.CHARS_PER_TOKEN
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Message:
        """
        Add a message to the conversation.
        
        Args:
            role: Message role (user, assistant, tool)
            content: Message content
            metadata: Optional metadata
            
        Returns:
            The created Message object
        """
        msg = Message(role=role, content=content, metadata=metadata)
        self.messages.append(msg)
        
        # Update token count
        self.total_tokens += self._estimate_tokens(content)
        
        logger.debug(f"Added {role} message ({len(content)} chars)")
        return msg
    
    def get_messages_for_api(self) -> List[Dict]:
        """
        Get messages formatted for API calls.
        
        Returns:
            List of message dictionaries
        """
        return [msg.to_dict() for msg in self.messages]
    
    def get_context_usage(self) -> float:
        """
        Get context window usage as percentage.
        
        Returns:
            0.0 to 1.0 (0% to 100% used)
        """
        used = self.system_tokens + self.total_tokens
        return min(used / self.max_tokens, 1.0)
    
    def get_remaining_tokens(self) -> int:
        """
        Get estimated remaining tokens.
        
        Returns:
            Number of tokens remaining
        """
        used = self.system_tokens + self.total_tokens
        return max(self.max_tokens - used, 0)
    
    def compact(self, keep_recent: int = 10) -> str:
        """
        Compress conversation by summarizing old messages.
        
        Args:
            keep_recent: Number of recent messages to keep as-is
            
        Returns:
            Summary of compacted messages
        """
        if len(self.messages) <= keep_recent:
            return "No compaction needed"
        
        # Messages to summarize
        old_messages = self.messages[:-keep_recent]
        
        # Create summary
        summary_parts = []
        user_msgs = [m for m in old_messages if m.role == "user"]
        assistant_msgs = [m for m in old_messages if m.role == "assistant"]
        
        summary_parts.append(f"Previous conversation summary:")
        summary_parts.append(f"- {len(user_msgs)} user messages")
        summary_parts.append(f"- {len(assistant_msgs)} assistant responses")
        
        if user_msgs:
            summary_parts.append(f"- Topics: {', '.join([m.content[:30] + '...' for m in user_msgs[-3:]])}")
        
        summary = "\n".join(summary_parts)
        
        # Replace old messages with summary
        summary_msg = Message(role="system", content=summary)
        self.messages = [summary_msg] + self.messages[-keep_recent:]
        
        # Recalculate tokens
        self.total_tokens = sum(self._estimate_tokens(m.content) for m in self.messages)
        
        logger.info(f"Compacted conversation: {len(old_messages)} messages -> summary + {keep_recent} recent")
        return summary
    
    def clear(self):
        """Clear all messages (keep system prompt)."""
        self.messages.clear()
        self.total_tokens = 0
        logger.info("Conversation cleared")
    
    def save(self, path: Path) -> bool:
        """
        Save conversation to file.
        
        Args:
            path: Path to save to
            
        Returns:
            True if successful
        """
        try:
            data = {
                "session_id": self.session_id,
                "max_tokens": self.max_tokens,
                "system_prompt": self.system_prompt,
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp,
                        "metadata": m.metadata
                    }
                    for m in self.messages
                ]
            }
            
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Conversation saved to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            return False
    
    def load(self, path: Path) -> bool:
        """
        Load conversation from file.
        
        Args:
            path: Path to load from
            
        Returns:
            True if successful
        """
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            self.session_id = data.get("session_id", self.session_id)
            self.max_tokens = data.get("max_tokens", self.max_tokens)
            self.system_prompt = data.get("system_prompt", self.system_prompt)
            self.system_tokens = self._estimate_tokens(self.system_prompt)
            
            self.messages = [
                Message(
                    role=m["role"],
                    content=m["content"],
                    timestamp=m.get("timestamp"),
                    metadata=m.get("metadata")
                )
                for m in data.get("messages", [])
            ]
            
            # Recalculate tokens
            self.total_tokens = sum(self._estimate_tokens(m.content) for m in self.messages)
            
            logger.info(f"Conversation loaded from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load conversation: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get conversation statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "user_messages": len([m for m in self.messages if m.role == "user"]),
            "assistant_messages": len([m for m in self.messages if m.role == "assistant"]),
            "estimated_tokens": self.system_tokens + self.total_tokens,
            "max_tokens": self.max_tokens,
            "context_usage": self.get_context_usage(),
            "remaining_tokens": self.get_remaining_tokens()
        }
