#!/usr/bin/env python3
"""
AI_SYNAPSE — Universal AI CLI v0.4.0

Your intelligent bridge to AI — adaptive, persistent, and future-proof.

Features:
- Multi-provider routing with auto-fallback
- CARL: Context-aware rule injection
- Memory: Project knowledge persistence  
- Skills: Structured workflows (TDD, Debugging)
- Session: Save/resume conversations
- Cache: Response caching for efficiency
- Web Search: Current information lookup
- Tools: File operations, bash commands

Usage:
    synapse                    # Interactive mode
    synapse "hello"            # Single message
    synapse --skill tdd "..."  # Use skill
    synapse --remember "..."   # Save to memory
"""

import sys
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add project to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.config import ConfigManager, get_config, SynapseConfig
from core.router import ProviderRouter
from core.carl import CARLSystem
from core.memory import MemorySystem
from core.skills import SkillSystem
from core.conversation import Conversation
from core.tools import ToolRegistry
from core.web_search import WebSearch
from core.cache import ResponseCache
from core.session_manager import SessionManager

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("synapse")


def print_banner():
    """Print the Synapse banner."""
    print("""
+------------------------------------------------------------------+
|  AI_SYNAPSE v0.4.0 — Universal AI Coding Assistant               |
|                                                                  |
|  Multi-Provider | CARL Intelligence | Persistent Memory          |
|  Skills | Agentic Tool Loop | Session Save | Web Search          |
+------------------------------------------------------------------+
    """)


def check_first_run():
    """Check if this is the first run and setup if needed."""
    config_manager = ConfigManager()
    
    if not config_manager.config_path.exists():
        print("👋 Welcome to AI_SYNAPSE!")
        print("\n🔧 Setting up your AI assistant...\n")
        
        # Create config
        config_manager.create_default_config()
        
        # Create necessary directories
        Path("~/.synapse/cache").expanduser().mkdir(parents=True, exist_ok=True)
        Path("~/.synapse/sessions").expanduser().mkdir(parents=True, exist_ok=True)
        
        print(f"✅ Configuration: ~/.synapse/config.yaml")
        print(f"✅ CARL rules: ~/.synapse/carl/")
        print(f"✅ Skills: ~/.synapse/skills/")
        print(f"✅ Memory: ~/.synapse/memory/")
        print(f"✅ Cache: ~/.synapse/cache/")
        print(f"✅ Sessions: ~/.synapse/sessions/")
        
        print("\n📖 Quick Start:")
        print("  1. Set API keys (optional):")
        print("     export GROQ_API_KEY='gsk_...'")
        print("     export GEMINI_API_KEY='...'")
        print("\n  2. Start chatting:")
        print("     ./synapse.py")
        print("\n  3. See the guide:")
        print("     cat USAGE_GUIDE.md")
        
        return True
    return False


async def handle_command(
    user_input: str,
    router: ProviderRouter,
    carl: CARLSystem,
    memory: MemorySystem,
    skills: SkillSystem,
    conversation: Conversation,
    tools: ToolRegistry,
    web_search: WebSearch,
    cache: ResponseCache,
    sessions: SessionManager,
    config: SynapseConfig,
    console=None,
    auto_approve: bool = False
):
    """Handle a single command/message."""
    
    # Special commands
    cmd = user_input.strip().lower()
    
    if cmd in ['/exit', '/quit', 'exit', 'quit']:
        # Save session before exit
        sessions.save_session(conversation, Path.cwd())
        print("\n👋 Session saved. Goodbye!")
        return 'exit'
    
    if cmd == '/compact':
        summary = conversation.compact()
        print(f"\n📝 {summary}\n")
        return 'continue'
    
    if cmd == '/clear':
        conversation.clear()
        print("\n🧹 Conversation cleared\n")
        return 'continue'
    
    if cmd == '/stats':
        stats = conversation.get_stats()
        cache_stats = cache.get_stats()
        print(f"\n📊 Session Stats:")
        print(f"   Session ID: {stats['session_id']}")
        print(f"   Messages: {stats['message_count']} total")
        print(f"   Context: {stats['context_usage']:.1%} used")
        print(f"   Remaining: {stats['remaining_tokens']:,} tokens")
        print(f"\n💾 Cache Stats:")
        print(f"   Entries: {cache_stats['entries']}")
        print(f"   Size: {cache_stats['total_size_mb']} MB")
        print()
        return 'continue'
    
    if cmd == '/save':
        session_id = sessions.save_session(conversation, Path.cwd())
        print(f"\n💾 Session saved: {session_id}\n")
        return 'continue'
    
    if cmd == '/sessions':
        saved = sessions.list_sessions()
        if saved:
            print(f"\n💾 Saved Sessions:")
            for i, s in enumerate(saved[:10], 1):
                preview = s.preview[:40] + "..." if len(s.preview) > 40 else s.preview
                print(f"  {i}. {s.session_id} - \"{preview}\" ({s.message_count} msgs)")
        else:
            print("\n📭 No saved sessions\n")
        return 'continue'
    
    if cmd.startswith('/load '):
        session_id = user_input[6:].strip()
        loaded = sessions.load_session(session_id)
        if loaded:
            # Copy loaded conversation
            conversation.messages = loaded.messages
            conversation.total_tokens = sum(len(m.content) // 4 for m in loaded.messages)
            conversation.session_id = loaded.session_id
            print(f"\n📂 Loaded session: {session_id}")
            print(f"   {len(loaded.messages)} messages restored\n")
        else:
            print(f"\n❌ Session not found: {session_id}\n")
        return 'continue'
    
    if cmd == '/cache':
        stats = cache.get_stats()
        print(f"\n💾 Cache Stats:")
        print(f"   Entries: {stats['entries']}")
        print(f"   Size: {stats['total_size_mb']} MB")
        print(f"   Location: {stats['cache_dir']}")
        print()
        return 'continue'
    
    if cmd == '/cache clear':
        cache.clear()
        print("\n🧹 Cache cleared\n")
        return 'continue'
    
    if cmd.startswith('/search '):
        query = user_input[8:].strip()
        print(f"\n🔍 Searching: {query}\n")
        results = web_search.search(query, max_results=5)
        print(web_search.format_results(results))
        print()
        return 'continue'
    
    if cmd == '/help':
        print("""
📖 Commands:
  /exit, exit      - Quit and save session
  /compact         - Summarize old messages
  /clear           - Clear conversation
  /stats           - Show session stats
  /save            - Save current session
  /sessions        - List saved sessions
  /load <id>       - Load a session
  /cache           - Show cache stats
  /cache clear     - Clear cache
  /search <query>  - Web search
  /help            - Show this help

✨ Star Commands (start message with):
  *dev, *debug, *plan, *review, *brief, *explain, *test

See USAGE_GUIDE.md for complete documentation.
""")
        return 'continue'
    
    # Regular message - process through AI
    return await process_ai_message(
        user_input, router, carl, memory, skills,
        conversation, tools, cache, config, console, auto_approve
    )


async def process_ai_message(
    message: str,
    router: ProviderRouter,
    carl: CARLSystem,
    memory: MemorySystem,
    skills: SkillSystem,
    conversation: Conversation,
    tools: ToolRegistry,
    cache: ResponseCache,
    config: SynapseConfig,
    console=None,
    auto_approve: bool = False
):
    """Process a message through the agentic AI pipeline."""
    from core.agent_loop import AgentLoop
    from core.agent_response import ResponseType

    # 1. CARL Processing
    context_usage = conversation.get_context_usage()
    carl_result = carl.process_message(message, context_usage)

    # Show what CARL detected
    if carl_result.star_command:
        print(f"  Mode: *{carl_result.star_command}")
    if carl_result.loaded_domains:
        print(f"  Context: {', '.join(carl_result.loaded_domains)}")

    # 2. Load Memory
    memory_content = ""
    if config.memory.enabled:
        memory_content = memory.load_for_project(Path.cwd())

    # 3. Detect Skills
    loaded_skills = skills.detect_skills(carl_result.modified_message)
    if loaded_skills:
        skill_names = [s.metadata.name for s in loaded_skills]
        print(f"  Skills: {', '.join(skill_names)}")

    # 4. Build System Prompt
    system_parts = [
        "You are AI_SYNAPSE, an intelligent coding assistant. "
        "You can read files, edit code, run commands, and search for files. "
        "Use the provided tools to help the user with their coding tasks. "
        "Always read files before editing them. Think step by step. "
        "Use relative file paths (e.g., 'requirements.txt', 'src/main.py') — not placeholder paths."
    ]
    if carl_result.rules:
        system_parts.append(carl.format_rules_for_prompt(carl_result.rules))
    if memory_content:
        system_parts.append(f"<project-memory>\n{memory_content}\n</project-memory>")
    if loaded_skills:
        system_parts.append(skills.format_for_prompt(loaded_skills))

    system_prompt = "\n\n".join(system_parts)
    conversation.system_prompt = system_prompt

    # Ensure system message is first in conversation
    if not conversation.messages or conversation.messages[0].role != "system":
        from core.conversation import Message
        conversation.messages.insert(0, Message(role="system", content=system_prompt))
    else:
        conversation.messages[0].content = system_prompt

    # 5. Run Agent Loop
    agent = AgentLoop(
        router=router,
        tools=tools,
        conversation=conversation,
        max_iterations=50,
        auto_approve=auto_approve
    )

    print()

    async for event in agent.run(carl_result.modified_message):
        if event.type == ResponseType.TEXT:
            print(event.text, end="", flush=True)

        elif event.type == ResponseType.TOOL_CALL:
            for tc in event.tool_calls:
                args_preview = str(tc.arguments)
                if len(args_preview) > 80:
                    args_preview = args_preview[:80] + "..."
                print(f"\n  [tool] {tc.name}({args_preview})")

        elif event.type == ResponseType.TOOL_RESULT:
            tr = event.tool_result
            status = "ok" if not tr.is_error else "error"
            output_preview = tr.output[:200] if tr.output else ""
            if len(tr.output) > 200:
                output_preview += "..."
            print(f"  [{status}] {output_preview}")

        elif event.type == ResponseType.ERROR:
            print(f"\n  Error: {event.text}")

        elif event.type == ResponseType.DONE:
            print()  # Final newline

    # Context warning
    if conversation.get_context_usage() > config.conversation.compact_threshold:
        print(f"\n  Context at {conversation.get_context_usage():.0%}. Use /compact or /clear\n")

    return 'continue'


async def chat_loop(config: SynapseConfig, auto_approve: bool = False):
    """Main interactive chat loop."""
    
    # Initialize all systems
    router = ProviderRouter(config)
    carl = CARLSystem(Path(config.carl.config_path))
    memory = MemorySystem(config.memory.location)
    skills = SkillSystem(config.skills.location)
    conversation = Conversation(max_tokens=config.conversation.max_tokens)
    tools = ToolRegistry()
    web_search = WebSearch()
    cache = ResponseCache("~/.synapse/cache")
    sessions = SessionManager("~/.synapse/sessions")
    
    try:
        from rich.console import Console
        console = Console()
    except ImportError:
        console = None
    
    print_banner()
    print("\n💡 Quick Tips:")
    print("   • Use *dev, *debug, *plan for different modes")
    print("   • Use /search <query> to search the web")
    print("   • Use /save to save conversation")
    print("   • Use /compact when context fills up")
    print("   • Type /help for all commands")
    print()
    
    while True:
        try:
            # Get input
            if console:
                user_input = console.input("[bold green]You:[/bold green] ")
            else:
                user_input = input("You: ")
            
            if not user_input.strip():
                continue
            
            # Process command
            result = await handle_command(
                user_input, router, carl, memory, skills,
                conversation, tools, web_search, cache, sessions, config, console, auto_approve
            )
            
            if result == 'exit':
                break
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            break


async def single_message(message: str, config: SynapseConfig, auto_approve: bool = False):
    """Process a single message and exit."""
    router = ProviderRouter(config)
    carl = CARLSystem(Path(config.carl.config_path))
    memory = MemorySystem(config.memory.location)
    skills = SkillSystem(config.skills.location)
    conversation = Conversation(max_tokens=config.conversation.max_tokens)
    tools = ToolRegistry()
    cache = ResponseCache("~/.synapse/cache")

    await process_ai_message(
        message, router, carl, memory, skills,
        conversation, tools, cache, config, None, auto_approve
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI_SYNAPSE — Universal AI CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  synapse                           # Interactive mode
  synapse "hello world"             # Single query
  synapse --skill tdd "add tests"   # Use TDD skill
  synapse --remember "uses FastAPI" # Save memory
  synapse --memory                  # Show memory
  synapse --search "Python 3.13"    # Web search
  synapse --export <session_id>     # Export conversation

Full guide: cat USAGE_GUIDE.md
        """
    )
    
    parser.add_argument("message", nargs="?", help="Message to send")
    parser.add_argument("--skill", "-s", action="append", help="Load skill")
    parser.add_argument("--remember", "-r", metavar="INFO", help="Remember info")
    parser.add_argument("--memory", "-m", action="store_true", help="Show memory")
    parser.add_argument("--forget", metavar="PATTERN", help="Forget pattern")
    parser.add_argument("--search", metavar="QUERY", help="Web search")
    parser.add_argument("--config", action="store_true", help="Show config")
    parser.add_argument("--export", metavar="SESSION_ID", help="Export session")
    parser.add_argument("--format", choices=["markdown", "json", "text"], default="markdown")
    parser.add_argument("--version", "-v", action="version", version="AI_SYNAPSE v0.4.0")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-approve all tool calls")

    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # First run setup
    if check_first_run():
        return 0
    
    # Load config
    try:
        config = get_config()
    except Exception as e:
        print(f"❌ Config error: {e}")
        return 1
    
    # Handle commands
    if args.config:
        print(f"Config: ~/.synapse/config.yaml")
        print(f"Version: {config.version}")
        print(f"\nProviders: {', '.join(config.providers.keys())}")
        print(f"CARL: {'✅' if config.carl.enabled else '❌'}")
        print(f"Memory: {'✅' if config.memory.enabled else '❌'}")
        print(f"Skills: {'✅' if config.skills.enabled else '❌'}")
        return 0
    
    # Initialize systems
    memory = MemorySystem(config.memory.location)
    sessions = SessionManager("~/.synapse/sessions")
    web_search = WebSearch()
    
    if args.search:
        print(f"🔍 Searching: {args.search}\n")
        results = web_search.search(args.search, max_results=5)
        print(web_search.format_results(results))
        return 0
    
    if args.remember:
        if memory.remember(Path.cwd(), args.remember):
            print(f"✅ Remembered: {args.remember}")
        return 0
    
    if args.forget is not None:
        if memory.forget(Path.cwd(), args.forget or None):
            print(f"✅ Forgot: {args.forget or 'all'}")
        return 0
    
    if args.memory:
        content = memory.recall(Path.cwd())
        if content:
            print(f"📝 Project Memory:\n{content}")
        else:
            print("📭 No memory for this project")
        return 0
    
    if args.export:
        exported = sessions.export_session(args.export, args.format)
        if exported:
            print(exported)
        else:
            print(f"❌ Session not found: {args.export}")
        return 0
    
    # Single message mode
    if args.message:
        asyncio.run(single_message(args.message, config, auto_approve=getattr(args, 'yes', False)))
        return 0

    # Interactive mode
    asyncio.run(chat_loop(config, auto_approve=getattr(args, 'yes', False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
