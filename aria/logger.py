"""
Trace logging system for ARIA.
Provides real-time rich console visualization and persistent Markdown trace files.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from aria.config import LOGS_DIR


class StepRecord:
    """Represents a single step taken by the agent."""

    def __init__(
        self,
        step_number: int,
        thought: str,
        action: Optional[str] = None,
        action_input: Optional[Dict[str, Any]] = None,
        observation: Optional[str] = None,
        duration: float = 0.0,
        is_final: bool = False,
    ):
        self.step_number = step_number
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.thought = thought
        self.action = action
        self.action_input = action_input or {}
        self.observation = observation
        self.duration = duration
        self.is_final = is_final


class AgentLogger:
    """Handles both real-time console display and structured file traces."""

    def __init__(self, task: str, provider: str, model: str, max_steps: int):
        self.task = task
        self.provider = provider
        self.model = model
        self.max_steps = max_steps
        self.console = Console()
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.steps: List[StepRecord] = []
        self.final_answer: Optional[str] = None
        self.status = "In Progress"

        # Unique log file path
        timestamp_str = self.start_time.strftime("%Y%m%d_%H%M%S")
        safe_task = "".join(c if c.isalnum() else "_" for c in task[:25]).strip("_")
        self.log_file = LOGS_DIR / f"trace_{timestamp_str}_{safe_task}.md"

    def log_start(self):
        """Display startup banner in terminal."""
        banner = Text()
        banner.append("🧠 ARIA — Autonomous Research & Intelligence Agent\n", style="bold magenta")
        banner.append(f"Task: {self.task}\n", style="bold white")
        banner.append(f"Provider: {self.provider.upper()} | Model: {self.model} | Max Steps: {self.max_steps}", style="dim")
        self.console.print(Panel(banner, border_style="magenta", expand=False))

    def log_step(
        self,
        step_number: int,
        thought: str,
        action: Optional[str] = None,
        action_input: Optional[Dict[str, Any]] = None,
        observation: Optional[str] = None,
        duration: float = 0.0,
        is_final: bool = False,
    ):
        """Log a completed step to the console and internal record."""
        record = StepRecord(
            step_number=step_number,
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation,
            duration=duration,
            is_final=is_final,
        )
        self.steps.append(record)

        # Terminal display
        self.console.rule(f"[bold cyan]Step {step_number} / {self.max_steps}[/bold cyan] ({duration:.2f}s)")

        # Thought
        if thought:
            self.console.print(f"[bold blue]💭 Thought:[/bold blue] [italic]{thought}[/italic]")

        # Action
        if action and not is_final:
            args_str = ", ".join(f"{k}={repr(v)}" for k, v in (action_input or {}).items())
            self.console.print(f"[bold yellow]🔧 Action:[/bold yellow] [bold]{action}[/bold]({args_str})")

        # Observation
        if observation:
            obs_preview = observation.strip()
            if len(obs_preview) > 300:
                obs_preview = obs_preview[:300] + f"... [[dim]+{len(observation)-300} chars[/dim]]"
            self.console.print(f"[bold green]👁️  Observation:[/bold green] {obs_preview}\n")

    def log_final(self, final_answer: str, status: str = "Completed"):
        """Record task completion."""
        self.end_time = datetime.now()
        self.final_answer = final_answer
        self.status = status

        total_duration = (self.end_time - self.start_time).total_seconds()

        self.console.rule("[bold green]🎯 Mission Complete[/bold green]")
        self.console.print(
            Panel(
                f"[bold green]Status: {status}[/bold green] (Total time: {total_duration:.1f}s, Steps: {len(self.steps)})\n\n"
                f"{final_answer[:600]}..." if len(final_answer) > 600 else final_answer,
                title="[bold]Final Response[/bold]",
                border_style="green",
            )
        )

        # Write trace file to disk
        self.save_trace_file()

    def log_error(self, message: str):
        """Log an error message to console."""
        self.console.print(f"[bold red]❌ Error:[/bold red] {message}")

    def save_trace_file(self):
        """Generate and save reviewable Markdown trace file."""
        total_duration = (
            (self.end_time - self.start_time).total_seconds()
            if self.end_time
            else (datetime.now() - self.start_time).total_seconds()
        )

        md = [
            f"# 📜 ARIA Agent Execution Trace",
            f"",
            f"| Metric | Details |",
            f"|---|---|",
            f"| **Task** | `{self.task}` |",
            f"| **Status** | **{self.status}** |",
            f"| **Provider** | `{self.provider}` |",
            f"| **Model** | `{self.model}` |",
            f"| **Started** | {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} |",
            f"| **Duration** | {total_duration:.2f} seconds |",
            f"| **Total Steps** | {len(self.steps)} / {self.max_steps} |",
            f"",
            f"---",
            f"",
            f"## 🔄 Step-by-Step Reasoning Loop",
            f"",
        ]

        for step in self.steps:
            md.append(f"### Step {step.step_number} ({step.timestamp})")
            md.append(f"⏱️ **Duration:** `{step.duration:.2f}s`\n")
            md.append(f"💭 **Thought:**\n> {step.thought}\n")

            if step.action and not step.is_final:
                md.append(f"🔧 **Action:** `{step.action}`")
                md.append(f"```json\n{step.action_input}\n```\n")

            if step.observation:
                md.append(f"👁️ **Observation:**\n```text\n{step.observation}\n```\n")

            md.append("---\n")

        if self.final_answer:
            md.append(f"## 🏁 Final Synthesis / Outcome")
            md.append(f"\n{self.final_answer}\n")

        self.log_file.write_text("\n".join(md), encoding="utf-8")
        self.console.print(f"[dim]📁 Execution trace saved to: [underline]{self.log_file.name}[/underline][/dim]")
