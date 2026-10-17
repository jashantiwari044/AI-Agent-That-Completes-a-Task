#!/usr/bin/env python3
"""
ARIA — Autonomous Research & Intelligence Agent
CLI Entry Point
"""

import sys
import argparse
from pathlib import Path
from aria import config
from aria.llm import LLMClient
from aria.tools import get_default_tools
from aria.logger import AgentLogger
from aria.agent import ReActAgent
from rich.console import Console
from rich.table import Table


def show_tools_table():
    """Print a clean table of available tools and exit."""
    console = Console()
    table = Table(title="🛠️  ARIA Registered Tool Suite", border_style="cyan")
    table.add_column("Tool Name", style="bold yellow", width=16)
    table.add_column("Description", style="white")
    table.add_column("Parameters", style="dim cyan", width=30)

    tools = get_default_tools()
    for name, tool in tools.items():
        params = ", ".join(tool.parameters.keys())
        table.add_row(name, tool.description, params)

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="ARIA: Autonomous Research & Intelligence Agent running a ReAct reasoning loop.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Research the current state of humanoid robots in 2026"
  python main.py "Analyze trends in solid state batteries" --provider groq
  python main.py "Summarize findings in report.txt" --file report.txt --provider ollama
  python main.py --list-tools
        """,
    )

    parser.add_argument(
        "task",
        nargs="?",
        default="",
        help="The objective or research question for ARIA to execute.",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        help="Optional local file path to include as primary context for the task.",
    )
    parser.add_argument(
        "--provider",
        "-p",
        choices=["groq", "ollama"],
        default=None,
        help=f"LLM provider to use (default from .env: '{config.LLM_PROVIDER}').",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Model name override (e.g. 'llama-3.3-70b-versatile' or 'llama2-uncensored:7b').",
    )
    parser.add_argument(
        "--max-steps",
        "-s",
        type=int,
        default=config.MAX_STEPS,
        help=f"Maximum allowed reasoning steps (default: {config.MAX_STEPS}).",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all registered tools with their parameters and exit.",
    )

    args = parser.parse_args()

    if args.list_tools:
        show_tools_table()
        sys.exit(0)

    task = args.task.strip()
    if not task:
        # If no positional task provided, prompt interactively
        console = Console()
        console.print("[bold cyan]Enter a task for ARIA:[/bold cyan] ", end="")
        try:
            task = input().strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

    if not task:
        print("Error: No task provided. Run with --help for usage.")
        sys.exit(1)

    # If --file is provided, enrich the task prompt with the file instruction
    if args.file:
        file_path = Path(args.file)
        task = f"{task}\n(Reference local file: '{file_path.name}'. Use 'read_file' tool to inspect it.)"

    # Initialize LLM Client
    try:
        llm = LLMClient(provider=args.provider, model=args.model)
    except Exception as e:
        console = Console()
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        sys.exit(1)

    # Initialize tools & logger
    tools = get_default_tools()
    logger = AgentLogger(
        task=task,
        provider=llm.provider,
        model=llm.active_model,
        max_steps=args.max_steps,
    )

    # Instantiate Agent & Run Loop
    agent = ReActAgent(
        llm=llm,
        tools=tools,
        logger=logger,
        max_steps=args.max_steps,
    )

    agent.run(task)


if __name__ == "__main__":
    main()
