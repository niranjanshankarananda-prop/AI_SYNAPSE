"""
AI_SYNAPSE — Session Manager

Save and resume conversations across sessions.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from core.conversation import Conversation

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Information about a saved session."""
    session_id: str
    created: datetime
    updated: datetime
    message_count: int
    preview: str
    project_path: Optional[str] = None


class SessionManager:
    """
    Manages saving and loading conversation sessions.
    
    Sessions are saved to ~/.synapse/sessions/
    and can be resumed later.
    
    Example:
        manager = SessionManager()
        
        # Save current session
        manager.save_session(conv, project_path="/path/to/project")
        
        # List saved sessions
        sessions = manager.list_sessions()
        
        # Resume a session
        conv = manager.load_session(sessions[0].session_id)
    """
    
    def __init__(self, sessions_dir: Path):
        self.sessions_dir = Path(sessions_dir).expanduser()
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def save_session(
        self,
        conversation: Conversation,
        project_path: Optional[Path] = None
    ) -> str:
        """
        Save a conversation session.
        
        Args:
            conversation: Conversation to save
            project_path: Optional project path for context
            
        Returns:
            Session ID
        """
        session_id = conversation.session_id
        session_path = self.sessions_dir / f"{session_id}.json"
        
        data = {
            "session_id": session_id,
            "created": conversation.messages[0].timestamp if conversation.messages else datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "project_path": str(project_path) if project_path else None,
            "max_tokens": conversation.max_tokens,
            "system_prompt": conversation.system_prompt,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                    "metadata": m.metadata
                }
                for m in conversation.messages
            ]
        }
        
        with open(session_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Session saved: {session_id}")
        return session_id
    
    def load_session(self, session_id: str) -> Optional[Conversation]:
        """
        Load a saved conversation session.
        
        Args:
            session_id: Session ID to load
            
        Returns:
            Conversation or None if not found
        """
        session_path = self.sessions_dir / f"{session_id}.json"
        
        if not session_path.exists():
            logger.warning(f"Session not found: {session_id}")
            return None
        
        try:
            with open(session_path, 'r') as f:
                data = json.load(f)
            
            conv = Conversation(
                max_tokens=data.get('max_tokens', 128000),
                system_prompt=data.get('system_prompt', ''),
                session_id=session_id
            )
            
            for msg_data in data.get('messages', []):
                conv.add_message(
                    role=msg_data['role'],
                    content=msg_data['content'],
                    metadata=msg_data.get('metadata')
                )
            
            logger.info(f"Session loaded: {session_id}")
            return conv
            
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None
    
    def list_sessions(self) -> List[SessionInfo]:
        """
        List all saved sessions.
        
        Returns:
            List of session info, sorted by most recent first
        """
        sessions = []
        
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                
                # Get preview from first user message
                preview = ""
                for msg in data.get('messages', []):
                    if msg.get('role') == 'user':
                        preview = msg.get('content', '')[:50]
                        break
                
                info = SessionInfo(
                    session_id=data['session_id'],
                    created=datetime.fromisoformat(data['created']),
                    updated=datetime.fromisoformat(data['updated']),
                    message_count=len(data.get('messages', [])),
                    preview=preview,
                    project_path=data.get('project_path')
                )
                
                sessions.append(info)
                
            except Exception as e:
                logger.warning(f"Failed to read session file {session_file}: {e}")
        
        # Sort by updated time, most recent first
        sessions.sort(key=lambda s: s.updated, reverse=True)
        
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a saved session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        session_path = self.sessions_dir / f"{session_id}.json"
        
        if not session_path.exists():
            return False
        
        try:
            session_path.unlink()
            logger.info(f"Session deleted: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    def export_session(self, session_id: str, format: str = "markdown") -> Optional[str]:
        """
        Export a session to various formats.
        
        Args:
            session_id: Session ID to export
            format: Export format (markdown, json, text)
            
        Returns:
            Exported content or None
        """
        conv = self.load_session(session_id)
        if not conv:
            return None
        
        if format == "json":
            return json.dumps({
                "session_id": session_id,
                "messages": [m.to_dict() for m in conv.messages]
            }, indent=2)
        
        elif format == "markdown":
            lines = [f"# Session: {session_id}\n"]
            
            for msg in conv.messages:
                if msg.role == "user":
                    lines.append(f"## User\n\n{msg.content}\n")
                elif msg.role == "assistant":
                    lines.append(f"## Assistant\n\n{msg.content}\n")
                elif msg.role == "system":
                    lines.append(f"*System: {msg.content[:100]}...*\n")
            
            return "\n".join(lines)
        
        elif format == "text":
            lines = [f"Session: {session_id}\n"]
            
            for msg in conv.messages:
                role_label = msg.role.upper()
                lines.append(f"\n{role_label}: {msg.content}\n")
            
            return "\n".join(lines)
        
        else:
            logger.error(f"Unknown export format: {format}")
            return None
    
    def cleanup_old_sessions(self, max_age_days: int = 30):
        """
        Delete sessions older than specified days.
        
        Args:
            max_age_days: Maximum age in days
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=max_age_days)
        deleted = 0
        
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                if mtime < cutoff:
                    session_file.unlink()
                    deleted += 1
            except:
                pass
        
        logger.info(f"Cleaned up {deleted} old sessions")
