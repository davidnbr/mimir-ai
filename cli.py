#!/usr/bin/env python3
"""
Jarvis CLI - Command-line interface.
Supports both simple mode and multi-agent mode.
"""
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner

from config import Config

console = Console()


def print_welcome():
    """Print welcome message."""
    mode = Config.print_status()
    model = Config.GEMINI_MODEL if Config.USE_GEMINI_ONLY else Config.CLAUDE_MODEL

    welcome = f"""
# JARVIS v0.1.0

Good evening, Sir. JARVIS online and ready to assist.

**Mode:** {mode}
**Model:** {model}

Type your request or 'quit' to exit.
Commands: /clear (reset history), /mode (show current mode)
"""
    console.print(
        Panel(
            Markdown(welcome),
            title="[bold blue]JARVIS[/bold blue]",
            border_style="blue",
        )
    )


def run_simple_mode():
    """Run simple single-agent mode."""
    from simple_workflow import SimpleJarvis

    jarvis = SimpleJarvis()

    while True:
        try:
            console.print("[bold blue]You:[/bold blue] ", end="")
            user_input = input().strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                console.print("\n[dim]JARVIS powering down. Good evening, Sir.[/dim]")
                break

            if user_input.lower() == "/clear":
                jarvis.clear_history()
                console.print("[dim]Conversation history cleared, Sir.[/dim]\n")
                continue

            if user_input.lower() == "/mode":
                console.print(f"[dim]Current mode: {Config.print_status()}[/dim]\n")
                continue

            # Stream response
            console.print("\n[bold green]JARVIS:[/bold green]")

            try:
                for chunk in jarvis.stream(user_input):
                    console.print(chunk, end="")
                console.print("\n")
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                console.print("[dim]Attempting to continue...[/dim]\n")

        except KeyboardInterrupt:
            console.print("\n\n[dim]JARVIS powering down. Good evening, Sir.[/dim]")
            break


def run_multi_agent_mode():
    """Run full multi-agent supervisor mode."""
    from uuid import uuid4
    from workflow import create_jarvis_workflow, stream_jarvis

    console.print("[dim]Initializing multi-agent systems...[/dim]")
    try:
        workflow = create_jarvis_workflow()
        console.print("[green]✓ All systems operational[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Initialization failed: {e}[/red]")
        sys.exit(1)

    thread_id = str(uuid4())

    while True:
        try:
            console.print("[bold blue]You:[/bold blue] ", end="")
            user_input = input().strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                console.print("\n[dim]JARVIS powering down. Good evening, Sir.[/dim]")
                break

            if user_input.lower() == "/mode":
                console.print(f"[dim]Current mode: {Config.print_status()}[/dim]\n")
                continue

            console.print()
            current_agent = None

            try:
                for event in stream_jarvis(
                    user_input, thread_id=thread_id, workflow=workflow
                ):
                    for agent_name, data in event.items():
                        if agent_name != current_agent:
                            if current_agent is not None:
                                console.print()
                            current_agent = agent_name
                            console.print(
                                f"\n[bold magenta]{agent_name}:[/bold magenta]"
                            )

                        if "messages" in data:
                            for msg in data["messages"]:
                                if hasattr(msg, "content") and msg.content:
                                    content = msg.content
                                    if isinstance(content, list):
                                        content = "\n".join(
                                            (
                                                c.get("text", str(c))
                                                if isinstance(c, dict)
                                                else str(c)
                                            )
                                            for c in content
                                        )
                                    console.print(Markdown(content))
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                console.print("[dim]Attempting to continue...[/dim]")

            console.print()

        except KeyboardInterrupt:
            console.print("\n\n[dim]JARVIS powering down. Good evening, Sir.[/dim]")
            break


def run_cli():
    """Main entry point - picks mode based on config."""
    print_welcome()

    if Config.SIMPLE_MODE:
        run_simple_mode()
    else:
        run_multi_agent_mode()


if __name__ == "__main__":
    run_cli()
