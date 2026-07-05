import os
import sys
import asyncio
import time
from pathlib import Path
import typer

# Ensure the project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent))

import config
import cli
from tools.mcp_client import LocalMCPClient
from tools.markdown import save_readme, validate_markdown
from agents.planner_agent import run_planner
from agents.analyzer_agent import run_analyzer
from agents.readme_agent import run_readme_generator

app = typer.Typer(help="README Copilot – Multi-Agent AI Documentation Generator")

async def run_documentation_flow(project_path: str):
    """Run the multi-agent orchestration workflow to generate a README.md."""
    start_time = time.time()
    loop = asyncio.get_running_loop()
    
    # 0. Setup and scan top level folder to bootstrap the planner
    resolved_path = str(Path(project_path).resolve())
    top_level_files = []
    try:
        for item in os.listdir(resolved_path):
            if item not in config.EXCLUDE_DIRS:
                top_level_files.append(item)
    except Exception as e:
        cli.print_error(f"Failed to scan target project directory: {str(e)}")
        raise typer.Exit(code=1)
        
    # 1. Planner Agent Stage
    cli.console.print()
    with cli.console.status("[bold cyan]Planner Agent Started...[/bold cyan]", spinner="dots") as status:
        try:
            plan = await loop.run_in_executor(None, lambda: run_planner(resolved_path, top_level_files))
            cli.print_success("Planner Agent Completed")
        except Exception as e:
            cli.print_error(f"Planner Agent Failed:\n{config.format_agent_error(e)}")
            raise typer.Exit(code=1)
            
    # 2. Project Analyzer Agent Stage (Needs active MCP Client)
    with cli.console.status("[bold cyan]Project Analyzer Agent Started (Scanning Repository)...[/bold cyan]", spinner="dots") as status:
        try:
            async with LocalMCPClient(resolved_path) as mcp_client:
                # Run the analyzer agent to scan and detect tech stack details
                profile = await run_analyzer(mcp_client)
                
                # Fetch directory tree to supply to README agent
                directory_tree = await mcp_client.read_directory_tree()
                cli.print_success("Project Analyzer Completed")
        except Exception as e:
            cli.print_error(f"Project Analyzer Agent Failed:\n{config.format_agent_error(e)}")
            raise typer.Exit(code=1)
            
    # 3. README Generator Agent Stage
    with cli.console.status("[bold cyan]README Generator Agent Started (Writing Documentation)...[/bold cyan]", spinner="dots") as status:
        try:
            readme_content = await loop.run_in_executor(None, lambda: run_readme_generator(profile, directory_tree))
            cli.print_success("README Generator Completed")
        except Exception as e:
            cli.print_error(f"README Generator Agent Failed:\n{config.format_agent_error(e)}")
            raise typer.Exit(code=1)
            
    # 4. Save and Validate Output
    try:
        validate_markdown(readme_content)
        saved_path = save_readme(resolved_path, readme_content)
        cli.print_success(f"Documentation Generated & saved successfully.")
    except Exception as e:
        cli.print_error(f"Failed to save README: {str(e)}")
        raise typer.Exit(code=1)
        
    duration = time.time() - start_time
    
    # 5. Render final summary
    cli.render_execution_summary(
        project_name=plan.project_name,
        planner_status="Completed",
        analyzer_status="Completed",
        readme_status="Completed",
        language=profile.primary_language,
        framework=profile.framework,
        frontend=profile.frontend_tech,
        database=profile.database,
        scanned=profile.files_scanned,
        ignored=profile.files_ignored,
        saved_path=saved_path,
        duration=duration
    )

@app.command()
def main(
    project_path: str = typer.Argument(
        None, 
        help="Path to the local software project folder to document."
    )
):
    """Main CLI entrypoint for README Copilot."""
    cli.print_welcome()
    
    # Check environment configuration
    try:
        config.validate_environment()
    except ValueError as e:
        cli.print_error(str(e))
        cli.console.print("\n[bold yellow]Setup Guide:[/bold yellow]")
        cli.console.print("1. Create a `.env` file in the application directory.")
        cli.console.print("2. Set [green]GEMINI_API_KEY=your_gemini_api_key[/green].\n")
        raise typer.Exit(code=1)
        
    # Prompt for project path if not supplied as argument
    if not project_path:
        project_path = typer.prompt("\nEnter Project Path")
        
    # Check if target project path exists
    target = Path(project_path)
    if not target.exists() or not target.is_dir():
        cli.print_error(f"The path '{project_path}' is not a valid directory.")
        raise typer.Exit(code=1)
        
    # Run the async flow using asyncio
    asyncio.run(run_documentation_flow(project_path))

if __name__ == "__main__":
    app()
