"""
AI_SYNAPSE — Agent Loop

The core agentic loop that makes AI_SYNAPSE a real coding assistant.
Sends messages to AI, executes tool calls, sends results back, repeats.
"""

import json
import logging
from typing import AsyncIterator, Optional
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel

from core.agent_response import AgentResponse, ResponseType, ToolCall, ToolResult
from core.tools import ToolRegistry
from core.router import ProviderRouter
from core.conversation import Conversation

logger = logging.getLogger(__name__)


class AgentLoop:
    """
    Orchestrates the agentic tool loop.

    Flow:
    1. Send user message + tool schemas to provider
    2. If provider returns tool calls -> execute tools -> add results -> go to 1
    3. If provider returns text -> display to user -> done
    4. Safety: max iterations prevent infinite loops

    Example:
        loop = AgentLoop(router, tools, conversation)
        async for event in loop.run("fix the bug in main.py"):
            if event.type == ResponseType.TEXT:
                print(event.text, end="")
            elif event.type == ResponseType.TOOL_CALL:
                print(f"[calling {event.tool_calls[0].name}]")
    """

    def __init__(
        self,
        router: ProviderRouter,
        tools: ToolRegistry,
        conversation: Conversation,
        console: Optional[Console] = None,
        max_iterations: int = 50,
        auto_approve: bool = False
    ):
        self.router = router
        self.tools = tools
        self.conversation = conversation
        self.console = console or Console()
        self.max_iterations = max_iterations
        self.auto_approve = auto_approve
        self.iteration_count = 0

    async def run(self, user_message: str) -> AsyncIterator[AgentResponse]:
        """
        Run the agentic loop for a user message.

        Args:
            user_message: The user's input

        Yields:
            AgentResponse events (text chunks, tool activities, done signal)
        """
        # Add user message to conversation
        self.conversation.add_message("user", user_message)
        self.iteration_count = 0

        # Get tool schemas in OpenAI format
        openai_tools = self.tools.get_openai_tools()

        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            logger.info(f"Agent loop iteration {self.iteration_count}/{self.max_iterations}")

            # Get messages for API
            messages = self.conversation.get_messages_for_api()

            # Collect full response
            text_buffer = ""
            tool_calls = []
            done = False

            try:
                async for response in self.router.complete_with_tools(
                    messages, openai_tools
                ):
                    if response.type == ResponseType.TEXT:
                        text_buffer += response.text
                        yield response  # Stream text to caller

                    elif response.type == ResponseType.TOOL_CALL:
                        tool_calls = response.tool_calls
                        yield response  # Notify caller of tool calls

                    elif response.type == ResponseType.DONE:
                        done = True

                    elif response.type == ResponseType.ERROR:
                        yield response
                        return

            except Exception as e:
                logger.error(f"Provider error in agent loop: {e}")
                yield AgentResponse(type=ResponseType.ERROR, text=str(e))
                return

            # If we got tool calls, execute them
            if tool_calls:
                # Save assistant message with tool calls
                tool_calls_data = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in tool_calls
                ]
                self.conversation.add_message(
                    "assistant",
                    text_buffer or "",
                    metadata={"tool_calls": tool_calls_data}
                )

                # Execute each tool call
                for tc in tool_calls:
                    result = await self._execute_tool(tc)

                    # Yield tool result for display
                    yield AgentResponse(
                        type=ResponseType.TOOL_RESULT,
                        tool_result=result
                    )

                    # Add tool result to conversation
                    self.conversation.add_message(
                        "tool",
                        result.output,
                        metadata={
                            "tool_call_id": tc.id,
                            "name": tc.name
                        }
                    )

                # Continue loop — send tool results back to AI
                continue

            # No tool calls — we have a final text response
            if text_buffer:
                self.conversation.add_message("assistant", text_buffer)

            yield AgentResponse(type=ResponseType.DONE, finish_reason="stop")
            return

        # Hit max iterations
        self.console.print(
            f"\n[yellow]Warning: Hit max iterations ({self.max_iterations}). "
            f"Stopping agent loop.[/yellow]"
        )
        yield AgentResponse(
            type=ResponseType.ERROR,
            text=f"Max iterations ({self.max_iterations}) reached"
        )

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a single tool call with permission checking.

        Args:
            tool_call: The tool call to execute

        Returns:
            ToolResult with output or error
        """
        tool_name = tool_call.name
        tool_args = {k: v for k, v in tool_call.arguments.items() if v is not None}

        logger.info(f"Executing tool: {tool_name}({tool_args})")

        # Get the tool
        tool = self.tools.get(tool_name)
        if not tool:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_name,
                output=f"Error: Unknown tool '{tool_name}'",
                is_error=True
            )

        # Permission check for bash commands
        if tool_name == "bash":
            command = tool_args.get("command", "")
            from core.tools import BashTool
            if isinstance(tool, BashTool) and tool.is_dangerous(command):
                if not self.auto_approve:
                    self.console.print(
                        Panel(
                            f"[yellow]Command:[/yellow] {command}",
                            title="Permission Required",
                            border_style="yellow"
                        )
                    )
                    if not Confirm.ask("Allow this command?"):
                        return ToolResult(
                            tool_call_id=tool_call.id,
                            name=tool_name,
                            output="User denied permission for this command",
                            is_error=True
                        )
                # Mark as confirmed
                tool_args["confirmed"] = True

        # Execute the tool
        try:
            output = tool.execute(**tool_args)

            # Truncate very long outputs
            if len(output) > 10000:
                output = output[:10000] + f"\n... (truncated, {len(output)} chars total)"

            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_name,
                output=output,
                is_error=False
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                name=tool_name,
                output=f"Error executing {tool_name}: {e}",
                is_error=True
            )
