"""
AI_SYNAPSE — Tool Integration

Built-in tools for file operations, command execution, etc.
These are provided to the AI for agentic workflows.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Abstract base class for tools."""
    
    name: str
    description: str
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> str:
        """Execute the tool with given arguments."""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict:
        """Get JSON schema for the tool."""
        pass


class ReadTool(Tool):
    """Read file contents."""
    
    name = "read"
    description = "Read the contents of a file"
    
    def execute(self, file_path: str, offset: int = 1, limit: Optional[int] = None) -> str:
        """
        Read file contents.
        
        Args:
            file_path: Path to file
            offset: Line number to start from (1-indexed)
            limit: Maximum lines to read
            
        Returns:
            File contents with line numbers
        """
        try:
            path = Path(file_path).expanduser()
            
            if not path.exists():
                return f"Error: File not found: {file_path}"
            
            if not path.is_file():
                return f"Error: Not a file: {file_path}"
            
            with open(path, 'r') as f:
                lines = f.readlines()
            
            # Apply offset and limit
            start = max(0, offset - 1)
            end = len(lines)
            if limit:
                end = min(start + limit, len(lines))
            
            lines = lines[start:end]
            
            # Format with line numbers
            result = []
            for i, line in enumerate(lines, start=start + 1):
                result.append(f"{i:4d}│ {line.rstrip()}")
            
            return "\n".join(result)
            
        except Exception as e:
            return f"Error reading file: {e}"
    
    def get_schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start from (1-indexed)",
                        "default": 1
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum lines to read"
                    }
                },
                "required": ["file_path"]
            }
        }


class EditTool(Tool):
    """Edit file contents (find and replace)."""
    
    name = "edit"
    description = "Edit a file by replacing text"
    
    def execute(self, file_path: str, old_string: str, new_string: str) -> str:
        """
        Edit file by replacing text.
        
        Args:
            file_path: Path to file
            old_string: Text to find
            new_string: Text to replace with
            
        Returns:
            Success message or error
        """
        try:
            path = Path(file_path).expanduser()
            
            if not path.exists():
                return f"Error: File not found: {file_path}"
            
            with open(path, 'r') as f:
                content = f.read()
            
            if old_string not in content:
                return f"Error: Could not find text to replace in {file_path}"
            
            # Count occurrences
            count = content.count(old_string)
            
            # Replace
            new_content = content.replace(old_string, new_string)
            
            with open(path, 'w') as f:
                f.write(new_content)
            
            return f"Successfully edited {file_path} ({count} replacement{'s' if count > 1 else ''})"
            
        except Exception as e:
            return f"Error editing file: {e}"
    
    def get_schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to edit"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Text to find and replace"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Text to replace with"
                    }
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        }


class WriteTool(Tool):
    """Write content to a file (creates or overwrites)."""
    
    name = "write"
    description = "Write content to a file (creates new file or overwrites existing)"
    
    def execute(self, file_path: str, content: str) -> str:
        """
        Write content to file.
        
        Args:
            file_path: Path to file
            content: Content to write
            
        Returns:
            Success message or error
        """
        try:
            path = Path(file_path).expanduser()
            
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                f.write(content)
            
            return f"Successfully wrote to {file_path}"
            
        except Exception as e:
            return f"Error writing file: {e}"
    
    def get_schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    }
                },
                "required": ["file_path", "content"]
            }
        }


class BashTool(Tool):
    """Execute bash commands."""
    
    name = "bash"
    description = "Execute a bash command"
    
    # Commands that are always allowed
    SAFE_COMMANDS = ['ls', 'pwd', 'cat', 'echo', 'grep', 'find', 'head', 'tail', 'wc', 'git status', 'git log', 'git diff']
    
    # Commands that require confirmation
    DANGEROUS_COMMANDS = ['rm', 'mv', 'cp', 'git push', 'git reset', 'git checkout', 'docker', 'sudo']
    
    def __init__(self, allowed_commands: Optional[List[str]] = None):
        self.allowed_commands = set(allowed_commands or [])
    
    def is_safe(self, command: str) -> bool:
        """Check if command is in safe list."""
        cmd_base = command.split()[0] if command else ''
        return cmd_base in self.SAFE_COMMANDS or command in self.allowed_commands
    
    def is_dangerous(self, command: str) -> bool:
        """Check if command might be dangerous."""
        for dangerous in self.DANGEROUS_COMMANDS:
            if command.startswith(dangerous):
                return True
        return False
    
    def execute(self, command: str, timeout: int = 60, confirmed: bool = False) -> str:
        """
        Execute bash command.

        Args:
            command: Command to execute
            timeout: Timeout in seconds
            confirmed: Whether user has confirmed (for dangerous commands)

        Returns:
            Command output or error
        """
        if self.is_dangerous(command) and not confirmed:
            return f"PERMISSION_REQUIRED: Command '{command}' requires confirmation (potentially dangerous)"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(f"stderr: {result.stderr}")
            
            if result.returncode != 0:
                output.append(f"Exit code: {result.returncode}")
            
            return "\n".join(output) if output else "Command completed (no output)"
            
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {e}"
    
    def get_schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bash command to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 60
                    }
                },
                "required": ["command"]
            }
        }


class GlobTool(Tool):
    """Find files matching a pattern."""
    
    name = "glob"
    description = "Find files matching a pattern (e.g., '*.py', 'src/**/*.ts')"
    
    def execute(self, pattern: str, path: str = ".") -> str:
        """
        Find files matching pattern.
        
        Args:
            pattern: Glob pattern
            path: Starting directory
            
        Returns:
            List of matching files
        """
        try:
            from pathlib import Path
            
            base_path = Path(path).expanduser()
            matches = list(base_path.rglob(pattern))
            
            if not matches:
                return f"No files found matching '{pattern}'"
            
            # Sort by modification time (newest first)
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            lines = [f"Found {len(matches)} file(s) matching '{pattern}':"]
            for match in matches[:50]:  # Limit to 50
                lines.append(f"  {match}")
            
            if len(matches) > 50:
                lines.append(f"  ... and {len(matches) - 50} more")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error searching files: {e}"
    
    def get_schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g., '*.py', '**/*.json')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Starting directory",
                        "default": "."
                    }
                },
                "required": ["pattern"]
            }
        }


class GrepTool(Tool):
    """Search file contents with regex."""
    
    name = "grep"
    description = "Search file contents using regex"
    
    def execute(self, pattern: str, path: str = ".", glob: Optional[str] = None) -> str:
        """
        Search file contents.
        
        Args:
            pattern: Regex pattern to search for
            path: Directory or file to search
            glob: Optional file pattern to limit search
            
        Returns:
            Matching lines with file paths
        """
        try:
            import re
            import subprocess
            
            # Use ripgrep if available, otherwise Python implementation
            try:
                cmd = ["rg", "-n", "--color=never", pattern]
                if glob:
                    cmd.extend(["-g", glob])
                cmd.append(path)
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")[:50]
                    return f"Found matches:\n" + "\n".join(lines)
                elif result.returncode == 1:
                    return "No matches found"
                else:
                    raise Exception(result.stderr)
                    
            except FileNotFoundError:
                # Fallback to Python implementation
                base_path = Path(path).expanduser()
                matches = []
                
                files = base_path.rglob(glob or "*") if glob else base_path.rglob("*")
                
                for file_path in files:
                    if not file_path.is_file():
                        continue
                    
                    try:
                        with open(file_path, 'r', errors='ignore') as f:
                            for i, line in enumerate(f, 1):
                                if re.search(pattern, line):
                                    matches.append(f"{file_path}:{i}:{line.strip()}")
                                    if len(matches) >= 50:
                                        break
                    except:
                        continue
                    
                    if len(matches) >= 50:
                        break
                
                if matches:
                    return f"Found {len(matches)} matches:\n" + "\n".join(matches[:50])
                else:
                    return "No matches found"
            
        except Exception as e:
            return f"Error searching: {e}"
    
    def get_schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search",
                        "default": "."
                    },
                    "glob": {
                        "type": "string",
                        "description": "Optional file pattern (e.g., '*.py')"
                    }
                },
                "required": ["pattern"]
            }
        }


class ToolRegistry:
    """Registry of all available tools."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default built-in tools."""
        self.register(ReadTool())
        self.register(EditTool())
        self.register(WriteTool())
        self.register(BashTool())
        self.register(GlobTool())
        self.register(GrepTool())
    
    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all tool names."""
        return list(self.tools.keys())
    
    def get_schemas(self) -> List[Dict]:
        """Get schemas for all tools."""
        return [tool.get_schema() for tool in self.tools.values()]

    def get_openai_tools(self) -> list[dict]:
        """Get tools formatted for OpenAI function calling API."""
        return [
            {
                "type": "function",
                "function": tool.get_schema()
            }
            for tool in self.tools.values()
        ]
    
    def execute(self, name: str, **kwargs) -> str:
        """
        Execute a tool by name.
        
        Args:
            name: Tool name
            **kwargs: Tool arguments
            
        Returns:
            Tool output
        """
        tool = self.get(name)
        if not tool:
            return f"Error: Unknown tool '{name}'"
        
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return f"Error executing {name}: {e}"
