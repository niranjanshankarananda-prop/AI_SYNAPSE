"""
AI_SYNAPSE — Memory System

Persistent project knowledge that persists across sessions.
Each project gets its own MEMORY.md file.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class MemorySystem:
    """
    Manages project-specific persistent memory.
    
    Memory is stored in ~/.synapse/memory/{project-key}/MEMORY.md
    and automatically loaded when working in that project.
    
    Example:
        memory = MemorySystem("~/.synapse/memory")
        
        # Load memory for current project
        context = memory.load_for_project("/path/to/myapp")
        
        # Remember something
        memory.remember("/path/to/myapp", "Uses FastAPI with Pydantic v2")
        
        # Read memory
        print(memory.recall("/path/to/myapp"))
    """
    
    def __init__(self, memory_dir: Path):
        self.memory_dir = Path(memory_dir).expanduser()
        self.memory_dir.mkdir(parents=True, exist_ok=True)
    
    def _sanitize_path(self, project_path: Path) -> str:
        """
        Convert project path to safe directory name.
        
        Args:
            project_path: Path to project directory
            
        Returns:
            Safe string for use as directory name
        """
        # Expand and resolve path
        resolved = Path(project_path).expanduser().resolve()
        
        # Convert to string and replace path separators
        # Use full path to avoid collisions between same-named directories
        safe_name = str(resolved).replace("/", "-").replace("\\", "-").replace(":", "")
        
        # Remove leading dash if present
        if safe_name.startswith("-"):
            safe_name = safe_name[1:]
        
        return safe_name
    
    def _detect_project_root(self, start_path: Path) -> Path:
        """
        Detect project root by looking for git repo or returning start_path.
        
        Args:
            start_path: Starting directory
            
        Returns:
            Project root path
        """
        start_path = Path(start_path).expanduser().resolve()
        
        # If start_path is a file, use its parent
        if start_path.is_file():
            start_path = start_path.parent
        
        # Look for .git directory
        current = start_path
        while current != current.parent:  # Stop at root
            if (current / ".git").exists():
                return current
            current = current.parent
        
        # Fall back to start_path
        return start_path
    
    def _get_memory_path(self, project_path: Path) -> Path:
        """
        Get path to MEMORY.md for a project.
        
        Args:
            project_path: Path to project
            
        Returns:
            Path to MEMORY.md file
        """
        project_key = self._sanitize_path(project_path)
        project_memory_dir = self.memory_dir / project_key
        project_memory_dir.mkdir(parents=True, exist_ok=True)
        return project_memory_dir / "MEMORY.md"
    
    def load_for_project(
        self,
        project_path: Path,
        max_lines: int = 200
    ) -> str:
        """
        Load MEMORY.md for a project.
        
        Args:
            project_path: Path to project directory
            max_lines: Maximum lines to load (default 200)
            
        Returns:
            Memory content or empty string if no memory exists
        """
        # Detect project root
        project_root = self._detect_project_root(project_path)
        memory_file = self._get_memory_path(project_root)
        
        if not memory_file.exists():
            logger.debug(f"No memory found for project: {project_root}")
            return ""
        
        try:
            with open(memory_file, 'r') as f:
                lines = f.readlines()
            
            # Truncate to max_lines
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines.append("\n... (truncated, more in memory file)\n")
            
            content = "".join(lines).strip()
            logger.debug(f"Loaded {len(lines)} lines from memory for {project_root}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return ""
    
    def remember(
        self,
        project_path: Path,
        key_info: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Add information to project memory.
        
        Args:
            project_path: Path to project
            key_info: Information to remember
            metadata: Optional metadata (author, timestamp, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        project_root = self._detect_project_root(project_path)
        memory_file = self._get_memory_path(project_root)
        
        try:
            # Ensure directory exists
            memory_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Build entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            if metadata and metadata.get('category'):
                entry = f"\n- [{metadata['category']}] ({timestamp}) {key_info}"
            else:
                entry = f"\n- ({timestamp}) {key_info}"
            
            # Append to file
            with open(memory_file, 'a') as f:
                f.write(entry)
            
            logger.info(f"Added to memory: {key_info[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remember: {e}")
            return False
    
    def recall(self, project_path: Path) -> str:
        """
        Alias for load_for_project.
        
        Args:
            project_path: Path to project
            
        Returns:
            Memory content
        """
        return self.load_for_project(project_path)
    
    def forget(
        self,
        project_path: Path,
        pattern: Optional[str] = None
    ) -> bool:
        """
        Remove information from memory.
        
        Args:
            project_path: Path to project
            pattern: If provided, remove lines matching this pattern
                    If None, clear all memory
            
        Returns:
            True if successful, False otherwise
        """
        project_root = self._detect_project_root(project_path)
        memory_file = self._get_memory_path(project_root)
        
        if not memory_file.exists():
            return True
        
        try:
            if pattern is None:
                # Clear all memory
                memory_file.unlink()
                logger.info(f"Cleared all memory for {project_root}")
            else:
                # Remove lines matching pattern
                import re
                with open(memory_file, 'r') as f:
                    lines = f.readlines()
                
                filtered = [line for line in lines if pattern not in line]
                
                with open(memory_file, 'w') as f:
                    f.writelines(filtered)
                
                removed = len(lines) - len(filtered)
                logger.info(f"Removed {removed} lines from memory")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to forget: {e}")
            return False
    
    def update(
        self,
        project_path: Path,
        old_pattern: str,
        new_info: str
    ) -> bool:
        """
        Update existing memory entry.
        
        Args:
            project_path: Path to project
            old_pattern: Pattern to find existing entry
            new_info: New information to replace with
            
        Returns:
            True if successful, False otherwise
        """
        project_root = self._detect_project_root(project_path)
        memory_file = self._get_memory_path(project_root)
        
        if not memory_file.exists():
            return False
        
        try:
            with open(memory_file, 'r') as f:
                content = f.read()
            
            if old_pattern not in content:
                logger.warning(f"Pattern not found in memory: {old_pattern}")
                return False
            
            # Replace first occurrence
            content = content.replace(old_pattern, new_info, 1)
            
            with open(memory_file, 'w') as f:
                f.write(content)
            
            logger.info(f"Updated memory: {old_pattern} -> {new_info[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return False
    
    def list_projects(self) -> List[Path]:
        """
        List all projects with memory.
        
        Returns:
            List of project paths (sanitized)
        """
        projects = []
        
        for item in self.memory_dir.iterdir():
            if item.is_dir() and (item / "MEMORY.md").exists():
                # Convert back to readable path
                # Note: This is best-effort, path separators are lost
                projects.append(item)
        
        return projects
    
    def get_stats(self, project_path: Path) -> dict:
        """
        Get memory statistics for a project.
        
        Args:
            project_path: Path to project
            
        Returns:
            Dictionary with stats
        """
        project_root = self._detect_project_root(project_path)
        memory_file = self._get_memory_path(project_root)
        
        if not memory_file.exists():
            return {
                'exists': False,
                'entries': 0,
                'lines': 0,
                'size_bytes': 0
            }
        
        try:
            with open(memory_file, 'r') as f:
                content = f.read()
                lines = content.split('\n')
                entries = len([l for l in lines if l.startswith('- ')])
            
            stats = {
                'exists': True,
                'entries': entries,
                'lines': len(lines),
                'size_bytes': memory_file.stat().st_size
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'exists': False, 'error': str(e)}
