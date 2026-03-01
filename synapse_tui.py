#!/usr/bin/env python3
"""
AI_SYNAPSE TUI — Beautiful Terminal UI like Kilo

Features:
- Kilo-like interface with panels and status bar
- Multi-line input with syntax highlighting
- Streaming responses
- File diff display
- CARL rules indicator
- Model selector
- Project memory status
- Provider fallback indicator
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime

# Rich imports for beautiful UI
from rich.console import Console, Group
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.syntax import Syntax
from rich.table import Table
from rich.align import Align
from rich.prompt import Prompt
from rich.status import Status

# Add project to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.config import get_config, ConfigManager
from core.carl import CARLSystem, ContextBracket
from core.memory import MemorySystem
from core.skills import SkillSystem
from core.cache import ResponseCache
from core.session_manager import SessionManager
from core.router import ProviderRouter


@dataclass
class TUIMessage:
    """Message in the chat."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str
    metadata: Optional[Dict] = None


class SynapseTUI:
    """
    Beautiful TUI for AI_SYNAPSE.
    
    Similar to Kilo CLI but with Synapse features.
    """
    
    def __init__(self):
        self.console = Console()
        self.config = get_config()
        
        # Initialize Synapse systems
        self.carl = CARLSystem(Path(self.config.carl.config_path))
        self.memory = MemorySystem(self.config.memory.location)
        self.skills = SkillSystem(self.config.skills.location)
        self.cache = ResponseCache("~/.synapse/cache")
        self.sessions = SessionManager("~/.synapse/sessions")
        self.router = ProviderRouter(self.config)
        
        # State
        self.current_model = "kilo/moonshotai/kimi-k2.5:free"
        self.messages: List[TUIMessage] = []
        self.project_path = Path.cwd()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.context_usage = 0.0
        
        # Available models (like Kilo)
        self.models = [
            "kilo/moonshotai/kimi-k2.5:free",
            "kilo/minimax/minimax-m2.5:free",
            "kilo/qwen/qwen3-235b-a22b-thinking-2507",
            "groq/llama-3.3-70b-versatile",
            "gemini/gemini-2.5-flash",
            "qwen/qwen3-32b:free",
            "qwen2.5-coder:32b",
        ]
    
    def create_header(self) -> Panel:
        """Create the header panel."""
        title = Text("⚡ AI_SYNAPSE v0.4.0", style="bold cyan")
        subtitle = Text("Multi-Provider • CARL Intelligence • Persistent Memory", style="dim")
        
        header_text = Group(title, subtitle)
        return Panel(header_text, border_style="cyan")
    
    def create_status_bar(self) -> Panel:
        """Create the status bar showing current state."""
        # Model info
        model_text = f"📡 {self.current_model}"
        
        # Context usage
        usage_color = "green"
        if self.context_usage > 0.6:
            usage_color = "yellow"
        if self.context_usage > 0.8:
            usage_color = "red"
        context_text = f"💾 Context: [{usage_color}]{self.context_usage:.0%}[/{usage_color}]"
        
        # Project
        project_name = self.project_path.name or str(self.project_path)
        project_text = f"📁 {project_name}"
        
        # Memory status
        memory = self.memory.load_for_project(self.project_path)
        memory_text = f"🧠 Memory: {'✓' if memory else '✗'}"
        
        status = f"{model_text}  │  {context_text}  │  {project_text}  │  {memory_text}"
        return Panel(status, border_style="blue", padding=(0, 1))
    
    def create_chat_display(self) -> Panel:
        """Create the chat display area."""
        if not self.messages:
            content = Text("\n💡 Start chatting! Type your message below.\n", style="dim italic", justify="center")
            return Panel(content, border_style="green", title="Chat", title_align="left")
        
        # Build message display
        lines = []
        for msg in self.messages[-20:]:  # Show last 20 messages
            if msg.role == "user":
                # User message
                header = Text("👤 You", style="bold green")
                lines.append(header)
                lines.append(Text(msg.content, style="green"))
                lines.append(Text(""))
                
            elif msg.role == "assistant":
                # Assistant message
                header = Text("🤖 Assistant", style="bold blue")
                lines.append(header)
                lines.append(Text(msg.content))
                lines.append(Text(""))
                
            elif msg.role == "system":
                # System message (CARL rules, etc.)
                if msg.metadata and msg.metadata.get("type") == "carl":
                    header = Text("⚙️ CARL", style="bold yellow")
                    lines.append(header)
                    lines.append(Text(msg.content, style="yellow"))
                    lines.append(Text(""))
                elif msg.metadata and msg.metadata.get("type") == "tool":
                    header = Text("🔧 Tool", style="bold magenta")
                    lines.append(header)
                    lines.append(Text(msg.content, style="magenta"))
                    lines.append(Text(""))
                else:
                    lines.append(Text(msg.content, style="dim"))
        
        content = Group(*lines) if lines else Text("No messages", style="dim")
        return Panel(content, border_style="green", title="Chat", title_align="left", height=30)
    
    def create_help_panel(self) -> Panel:
        """Create help panel with commands."""
        commands = [
            ("/model", "Change model"),
            ("/models", "List models"),
            ("/clear", "Clear chat"),
            ("/compact", "Summarize context"),
            ("/save", "Save session"),
            ("/load <id>", "Load session"),
            ("/sessions", "List sessions"),
            ("/memory", "Show project memory"),
            ("/search <q>", "Web search"),
            ("/help", "Show help"),
            ("/exit", "Quit"),
            ("", ""),
            ("Star commands:", ""),
            ("*dev, *debug", "Mode commands"),
            ("*plan, *review", "Mode commands"),
        ]
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="dim")
        
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        
        return Panel(table, border_style="yellow", title="Commands", title_align="left", width=40)
    
    def render_full(self) -> Layout:
        """Render the full TUI layout."""
        layout = Layout()
        
        # Split into sections
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="main"),
            Layout(name="status", size=3)
        )
        
        # Header
        layout["header"].update(self.create_header())
        
        # Main area split into chat and help
        layout["main"].split_row(
            Layout(name="chat", ratio=3),
            Layout(name="help", ratio=1)
        )
        layout["main"]["chat"].update(self.create_chat_display())
        layout["main"]["help"].update(self.create_help_panel())
        
        # Status bar
        layout["status"].update(self.create_status_bar())
        
        return layout
    
    async def call_provider(self, message: str) -> str:
        """Call the AI provider through the agent loop."""
        from core.agent_loop import AgentLoop
        from core.agent_response import ResponseType
        from core.conversation import Conversation
        from core.tools import ToolRegistry

        # 1. CARL Processing
        carl_result = self.carl.process_message(message, self.context_usage)

        if carl_result.star_command:
            self.messages.append(TUIMessage(
                role="system",
                content=f"Mode: *{carl_result.star_command}",
                timestamp=datetime.now().isoformat(),
                metadata={"type": "carl"}
            ))

        if carl_result.loaded_domains:
            self.messages.append(TUIMessage(
                role="system",
                content=f"Context: {', '.join(carl_result.loaded_domains)}",
                timestamp=datetime.now().isoformat(),
                metadata={"type": "carl"}
            ))

        # 2. Load Memory
        memory_content = self.memory.load_for_project(self.project_path)

        # 3. Detect Skills
        loaded_skills = self.skills.detect_skills(carl_result.modified_message)
        if loaded_skills:
            skill_names = [s.metadata.name for s in loaded_skills]
            self.messages.append(TUIMessage(
                role="system",
                content=f"Skills: {', '.join(skill_names)}",
                timestamp=datetime.now().isoformat(),
                metadata={"type": "carl"}
            ))

        # 4. Build system prompt
        system_parts = [
            "You are AI_SYNAPSE, an intelligent coding assistant. "
            "Use the provided tools to help the user."
        ]
        if carl_result.rules:
            system_parts.append("\n".join([f"- {r}" for r in carl_result.rules]))
        if memory_content:
            system_parts.append(f"Project Context:\n{memory_content}")
        if loaded_skills:
            for skill in loaded_skills:
                system_parts.append(f"Skill ({skill.metadata.name}):\n{skill.content}")

        system_prompt = "\n\n".join(system_parts)

        # 5. Create conversation and run agent loop
        conversation = Conversation(max_tokens=128000, system_prompt=system_prompt)
        from core.conversation import Message
        conversation.messages.append(Message(role="system", content=system_prompt))

        # Add history from TUI messages
        for msg in self.messages[-20:]:  # Last 20 for context
            if msg.role in ("user", "assistant"):
                conversation.add_message(msg.role, msg.content)

        tools = ToolRegistry()
        agent = AgentLoop(
            router=self.router,
            tools=tools,
            conversation=conversation,
            console=self.console,
            max_iterations=50,
            auto_approve=False
        )

        response_parts = []

        async for event in agent.run(carl_result.modified_message):
            if event.type == ResponseType.TEXT:
                response_parts.append(event.text)
            elif event.type == ResponseType.TOOL_CALL:
                for tc in event.tool_calls:
                    tool_msg = f"[Tool: {tc.name}]"
                    self.messages.append(TUIMessage(
                        role="system", content=tool_msg,
                        timestamp=datetime.now().isoformat(),
                        metadata={"type": "tool"}
                    ))
            elif event.type == ResponseType.TOOL_RESULT:
                tr = event.tool_result
                preview = tr.output[:100] + "..." if len(tr.output) > 100 else tr.output
                self.messages.append(TUIMessage(
                    role="system", content=preview,
                    timestamp=datetime.now().isoformat(),
                    metadata={"type": "tool"}
                ))
            elif event.type == ResponseType.ERROR:
                response_parts.append(f"Error: {event.text}")

        return "".join(response_parts)
    
    def handle_command(self, command: str) -> bool:
        """Handle special commands. Returns True if handled, False to continue."""
        cmd = command.strip().lower()
        
        if cmd == "/exit":
            self.sessions.save_session(
                type('obj', (object,), {
                    'session_id': self.session_id,
                    'messages': [{'role': m.role, 'content': m.content} for m in self.messages],
                    'system_prompt': '',
                    'max_tokens': 128000
                })(),
                self.project_path
            )
            self.console.print("\n[green]👋 Session saved. Goodbye![/green]\n")
            return True
        
        if cmd == "/clear":
            self.messages.clear()
            self.context_usage = 0.0
            self.console.print("[green]🧹 Chat cleared[/green]\n")
            return False
        
        if cmd == "/models":
            self.console.print("\n[bold]Available Models:[/bold]")
            for i, model in enumerate(self.models, 1):
                marker = " →" if model == self.current_model else "  "
                self.console.print(f"{marker} {i}. {model}")
            self.console.print()
            return False
        
        if cmd.startswith("/model "):
            idx = command[7:].strip()
            try:
                if idx.isdigit():
                    self.current_model = self.models[int(idx) - 1]
                else:
                    self.current_model = idx
                self.console.print(f"[green]✓ Model changed to: {self.current_model}[/green]\n")
            except:
                self.console.print(f"[red]✗ Invalid model: {idx}[/red]\n")
            return False
        
        if cmd == "/memory":
            content = self.memory.recall(self.project_path)
            if content:
                self.console.print(Panel(content, title="Project Memory", border_style="green"))
            else:
                self.console.print("[dim]No memory for this project[/dim]\n")
            return False
        
        if cmd.startswith("/remember "):
            info = command[10:].strip()
            if self.memory.remember(self.project_path, info):
                self.console.print(f"[green]✓ Remembered: {info}[/green]\n")
            return False
        
        if cmd == "/sessions":
            sessions = self.sessions.list_sessions()
            if sessions:
                self.console.print("\n[bold]Saved Sessions:[/bold]")
                for s in sessions[:10]:
                    self.console.print(f"  {s.session_id} - {s.message_count} msgs")
            else:
                self.console.print("[dim]No saved sessions[/dim]\n")
            return False
        
        if cmd.startswith("/search "):
            query = command[8:].strip()
            self.console.print(f"\n[yellow]🔍 Searching: {query}[/yellow]\n")
            from core.web_search import WebSearch
            web = WebSearch()
            results = web.search(query)
            self.console.print(web.format_results(results))
            return False
        
        if cmd == "/help":
            self.console.print(Panel(self.create_help_panel().renderable, border_style="yellow"))
            return False
        
        return False
    
    async def run(self):
        """Main TUI loop."""
        # Initial render
        self.console.clear()
        layout = self.render_full()
        self.console.print(layout)
        
        while True:
            try:
                # Get input
                self.console.print()
                user_input = Prompt.ask("[bold green]You[/bold green]")
                
                if not user_input.strip():
                    continue
                
                # Check for commands
                if user_input.startswith("/"):
                    should_exit = self.handle_command(user_input)
                    if should_exit:
                        break
                    
                    # Re-render
                    self.console.clear()
                    self.console.print(self.render_full())
                    continue
                
                # Add user message
                self.messages.append(TUIMessage(
                    role="user",
                    content=user_input,
                    timestamp=datetime.now().isoformat()
                ))
                
                # Update display
                self.console.clear()
                self.console.print(self.render_full())
                
                # Get AI response
                self.console.print(f"\n[bold blue]Assistant[/bold blue] ", end="")
                
                response = await self.call_provider(user_input)
                
                # Add assistant message
                self.messages.append(TUIMessage(
                    role="assistant",
                    content=response,
                    timestamp=datetime.now().isoformat()
                ))
                
                # Print response
                self.console.print(response)
                
                # Update context usage
                total_chars = sum(len(m.content) for m in self.messages)
                self.context_usage = min(total_chars / (128000 * 4), 1.0)
                
                # Warning if high
                if self.context_usage > 0.75:
                    self.console.print(f"\n[yellow]⚠️  Context at {self.context_usage:.0%}. Use /compact[/yellow]")
                
                # Re-render
                self.console.clear()
                self.console.print(self.render_full())
                
            except KeyboardInterrupt:
                self.console.print("\n\n[green]👋 Goodbye![/green]")
                break
            except EOFError:
                break


async def main():
    """Entry point."""
    # Check first run
    config_manager = ConfigManager()
    if not config_manager.config_path.exists():
        console = Console()
        console.print("[bold cyan]👋 Welcome to AI_SYNAPSE TUI![/bold cyan]\n")
        config_manager.create_default_config()
        console.print("[green]✅ Configuration created[/green]\n")
    
    # Run TUI
    tui = SynapseTUI()
    await tui.run()


if __name__ == "__main__":
    asyncio.run(main())
