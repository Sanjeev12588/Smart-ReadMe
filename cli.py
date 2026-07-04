import sys
import time
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.status import Status
from rich.live import Live

console = Console()
stderr_console = Console(stderr=True)

def print_welcome():
    """Display the welcome screen banner."""
    welcome_text = Text("\n"
        "=========================================\n"
        "             README COPILOT              \n"
        "=========================================\n",
        style="cyan bold"
    )
    subtitle = Text("AI-Powered Multi-Agent Documentation Generator\n", style="italic blue")
    
    panel = Panel(
        Text.assemble(welcome_text, "\n", subtitle),
        border_style="cyan",
        title="[bold white]v1.0.0-MVP[/bold white]",
        title_align="right"
    )
    console.print(panel)

def print_success(message: str):
    """Print standard success message."""
    console.print(f"[bold green][+][/bold green] [white]{message}[/white]")

def print_error(message: str):
    """Print standard error message."""
    stderr_console.print(f"[bold red][x][/bold red] [red]{message}[/red]")

def print_warning(message: str):
    """Print standard warning message."""
    console.print(f"[bold yellow][!][/bold yellow] [yellow]{message}[/yellow]")

def render_execution_summary(
    project_name: str,
    planner_status: str,
    analyzer_status: str,
    readme_status: str,
    language: str,
    framework: str,
    frontend: str,
    database: str,
    scanned: int,
    ignored: int,
    saved_path: str,
    duration: float
):
    """Renders a gorgeous execution summary panel."""
    console.print("\n")
    
    # Status table
    status_table = Table.grid(padding=(0, 2))
    status_table.add_column("Agent", style="bold cyan", width=20)
    status_table.add_column("Status", width=15)
    
    status_table.add_row("Planner Agent", f"[green][OK] {planner_status}[/green]")
    status_table.add_row("Analyzer Agent", f"[green][OK] {analyzer_status}[/green]")
    status_table.add_row("README Agent", f"[green][OK] {readme_status}[/green]")
    
    # Metadata table
    meta_table = Table.grid(padding=(0, 2))
    meta_table.add_column("Key", style="dim white", width=20)
    meta_table.add_column("Value", style="bold green", width=30)
    
    meta_table.add_row("Primary Language", language or "None")
    meta_table.add_row("API Framework", framework or "None")
    meta_table.add_row("Frontend Tech", frontend or "None")
    meta_table.add_row("Database System", database or "None")
    meta_table.add_row("Files Scanned", str(scanned))
    meta_table.add_row("Files Ignored", str(ignored))
    
    summary_content = Group(
        Text("Project: ", style="bold white") + Text(f"{project_name}\n", style="bold yellow"),
        Text("\nAGENT WORKFLOW STATUS", style="bold underline white"),
        status_table,
        Text("\nTECHNOLOGY PROFILE", style="bold underline white"),
        meta_table,
        Text("\nSAVED TO:", style="bold white"),
        Text(f"{saved_path}\n", style="bold green"),
        Text(f"Total Time: {duration:.2f} seconds", style="italic blue")
    )
    
    panel = Panel(
        summary_content,
        title="[bold yellow]README COPILOT EXECUTION SUMMARY[/bold yellow]",
        border_style="yellow",
        padding=(1, 2)
    )
    console.print(panel)
