#!/usr/bin/env python3
"""
Jarvis CLI - Command-line interface with memory support.
"""
import sys
from uuid import uuid4

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from config import Config

console = Console()


def print_welcome():
    """Print welcome message."""
    mode = Config.print_status()
    model = Config.GEMINI_MODEL if Config.USE_GEMINI_ONLY else Config.CLAUDE_MODEL

    welcome = f"""
# JARVIS v0.2.0

Good evening, Sir. JARVIS online with memory systems active.

**Mode:** {mode}
**Model:** {model}

**Commands:**
- `/clear` - Clear session history
- `/memory` - Show memory statistics  
- `/patterns` - Show detected patterns
- `/sessions` - List past sessions
- `/recall <query>` - Search memories
- `/quit` - Exit

Type your request to begin.
"""
    console.print(
        Panel(
            Markdown(welcome),
            title="[bold blue]JARVIS[/bold blue]",
            border_style="blue",
        )
    )


def run_simple_mode():
    """Run simple single-agent mode with memory."""
    from simple_workflow import SimpleJarvis

    # Generate or reuse session ID
    session_id = str(uuid4())
    console.print(f"[dim]Session: {session_id[:8]}...[/dim]\n")

    jarvis = SimpleJarvis(session_id=session_id)

    # Show memory stats on start
    stats = jarvis.get_memory_stats()
    if stats["total_messages"] > 0:
        console.print(
            f"[dim]Memory: {stats['total_messages']} messages across {stats['total_sessions']} sessions[/dim]\n"
        )

    try:
        while True:
            try:
                console.print("[bold blue]You:[/bold blue] ", end="")
                user_input = input().strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ("quit", "exit", "q", "/quit"):
                    console.print(
                        "\n[dim]JARVIS powering down. Memories preserved, Sir.[/dim]"
                    )
                    break

                if user_input.lower() == "/clear":
                    jarvis.clear_history()
                    console.print(
                        "[dim]Session history cleared. Persistent memory intact, Sir.[/dim]\n"
                    )
                    continue

                if user_input.lower() == "/memory":
                    stats = jarvis.get_memory_stats()
                    table = Table(title="Memory Statistics")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")
                    table.add_row("Total Messages", str(stats["total_messages"]))
                    table.add_row("Total Sessions", str(stats["total_sessions"]))
                    table.add_row("Tracked Patterns", str(stats["total_patterns"]))
                    table.add_row("Embedded Chunks", str(stats["embedded_chunks"]))
                    console.print(table)
                    console.print()
                    continue

                if user_input.lower() == "/patterns":
                    patterns = jarvis.get_patterns()
                    if patterns:
                        table = Table(title="Detected Patterns")
                        table.add_column("Type", style="cyan")
                        table.add_column("Pattern", style="green")
                        table.add_column("Frequency", style="yellow")
                        for p in patterns[:10]:
                            table.add_row(
                                p["pattern_type"],
                                p["pattern_data"],
                                str(p["frequency"]),
                            )
                        console.print(table)
                    else:
                        console.print(
                            "[dim]No patterns detected yet, Sir. Keep chatting.[/dim]"
                        )
                    console.print()
                    continue

                if user_input.lower() == "/sessions":
                    sessions = jarvis.memory.get_all_sessions()
                    if sessions:
                        table = Table(title="Past Sessions")
                        table.add_column("Session ID", style="cyan")
                        table.add_column("Started", style="green")
                        table.add_column("Messages", style="yellow")
                        for s in sessions[:10]:
                            table.add_row(
                                s["session_id"][:8] + "...",
                                s["started"][:16] if s["started"] else "N/A",
                                str(s["message_count"]),
                            )
                        console.print(table)
                    else:
                        console.print("[dim]No past sessions found, Sir.[/dim]")
                    console.print()
                    continue

                if user_input.lower().startswith("/recall "):
                    query = user_input[8:].strip()
                    if query:
                        memories = jarvis.memory.recall(query, n_results=5)
                        if memories:
                            console.print(
                                f"\n[bold]Memories related to '{query}':[/bold]\n"
                            )
                            for i, mem in enumerate(memories, 1):
                                relevance = f"{mem['relevance']:.0%}"
                                console.print(f"[dim]{i}. ({relevance} match)[/dim]")
                                console.print(f"   {mem['content'][:200]}...\n")
                        else:
                            console.print("[dim]No relevant memories found, Sir.[/dim]")
                    console.print()
                    continue

                if user_input.lower() == "/mode":
                    console.print(f"[dim]Current mode: {Config.print_status()}[/dim]\n")
                    continue

                # Regular chat
                console.print("\n[bold green]JARVIS:[/bold green]")

                try:
                    for chunk in jarvis.stream(user_input):
                        console.print(chunk, end="")
                    console.print("\n")
                except Exception as e:
                    console.print(f"\n[red]Error: {e}[/red]")
                    console.print("[dim]Attempting to continue...[/dim]\n")

            except KeyboardInterrupt:
                console.print(
                    "\n\n[dim]JARVIS powering down. Memories preserved, Sir.[/dim]"
                )
                break
    finally:
        jarvis.close()


def run_cli():
    """Main entry point."""
    print_welcome()

    if Config.SIMPLE_MODE:
        run_simple_mode()
    else:
        # Multi-agent mode - not updated yet
        console.print(
            "[yellow]Multi-agent mode not yet updated for Phase 2. Using simple mode.[/yellow]\n"
        )
        run_simple_mode()


if __name__ == "__main__":
    run_cli()
