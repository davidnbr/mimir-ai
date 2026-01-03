#!/usr/bin/env python3
"""
Jarvis CLI - Simple command-line interface for Phase 1 testing.
Run with: python cli.py
"""
import sys
from uuid import uuid4

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner

from config import Config

console = Console()


def print_welcome():
    mode = Config.print_status()
    model = Config.GEMINI_MODEL if Config.USE_GEMINI_ONLY else Config.CLAUDE_MODEL

    """Print welcome message."""
    welcome = """
# JARVIS v0.1.0

Good evening, Sir. JARVIS online and ready to assist.

**Mode:** {mode}
**Model:** {model}

**Available Agents:**
- `prompt_refiner` - Clarifies your requests
- `backend_agent` - Python, Go, APIs, databases
- `frontend_agent` - React, TypeScript, CSS
- `devops_agent` - Terraform, Docker, Kubernetes, CI/CD
- `pr_reviewer` - Code quality review

Type your request or 'quit' to exit.
"""
    console.print(
        Panel(
            Markdown(welcome),
            title="[bold blue]JARVIS[/bold blue]",
            border_style="blue",
        )
    )


def format_agent_name(name: str) -> str:
    """Format agent name for display."""
    colors = {
        "prompt_refiner": "yellow",
        "backend_agent": "green",
        "frontend_agent": "cyan",
        "devops_agent": "magenta",
        "pr_reviewer": "red",
        "supervisor": "blue",
    }
    color = colors.get(name, "white")
    return f"[bold {color}]{name}[/bold {color}]"


def run_cli():
    """Run the interactive CLI."""
    print_welcome()

    # Create workflow once
    console.print("[dim]Initializing JARVIS systems...[/dim]")
    try:
        workflow = create_jarvis_workflow()
        console.print("[green]✓ All systems operational[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Initialization failed: {e}[/red]")
        sys.exit(1)

    # Unique thread ID for this session
    thread_id = str(uuid4())

    while True:
        try:
            # Get user input
            console.print("[bold blue]You:[/bold blue] ", end="")
            user_input = input().strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                console.print("\n[dim]JARVIS powering down. Good evening, Sir.[/dim]")
                break

            # Stream response
            console.print()
            current_agent = None

            with Live(
                Spinner("dots", text="Processing..."),
                refresh_per_second=10,
                transient=True,
            ):
                for event in stream_jarvis(
                    user_input, thread_id=thread_id, workflow=workflow
                ):
                    # event is a dict with agent name as key
                    for agent_name, data in event.items():
                        if agent_name != current_agent:
                            if current_agent is not None:
                                console.print()  # Newline between agents
                            current_agent = agent_name
                            console.print(f"\n{format_agent_name(agent_name)}:")

                        # Extract message content
                        if "messages" in data:
                            for msg in data["messages"]:
                                if hasattr(msg, "content") and msg.content:
                                    # Handle different content types
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

            console.print()

        except KeyboardInterrupt:
            console.print("\n\n[dim]JARVIS powering down. Good evening, Sir.[/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[dim]Attempting to continue...[/dim]\n")


if __name__ == "__main__":
    run_cli()
