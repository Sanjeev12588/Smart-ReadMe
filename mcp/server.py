import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager

_start_time = time.perf_counter()

def log_stderr(message: str):
    elapsed = time.perf_counter() - _start_time
    print(f"[MCP_SERVER_STARTUP] {elapsed:6.3f}s - {message}", file=sys.stderr, flush=True)

log_stderr("Process started")

import os
import fnmatch
log_stderr("Imports: os, fnmatch loaded")

log_stderr("Imports: loading fastmcp...")
from fastmcp import FastMCP
log_stderr("Imports: fastmcp loaded")

import json
log_stderr("Imports: json loaded")

# Add parent directory to path so imports work correctly when run from subprocess
sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
log_stderr("Imports: config loaded")

log_stderr("Creating FastMCP instance...")
@asynccontextmanager
async def server_lifespan(server):
    log_stderr("Initialize request received (FastMCP lifespan started)")
    yield
    log_stderr("Session teardown completed (FastMCP lifespan ended)")

mcp = FastMCP("readme-copilot-server", lifespan=server_lifespan)
log_stderr("FastMCP instance created with lifespan hooks")
log_stderr("Registering tools...")

def is_ignored(relative_path: Path) -> bool:
    """Check if the path should be ignored according to global exclusions."""
    for part in relative_path.parts:
        if part in config.EXCLUDE_DIRS:
            return True
    if relative_path.name in config.EXCLUDE_FILES:
        return True
    return False

@mcp.tool()
def list_files(project_path: str) -> str:
    """
    Lists all files in the target project path recursively, skipping ignored files and directories.
    Returns a JSON string representing a list of relative file paths.
    Capped at 500 files to prevent token overflow.
    """
    try:
        base_path = Path(project_path).resolve()
        if not base_path.exists():
            return json.dumps({"error": f"Path '{project_path}' does not exist."})
        
        MAX_FILES = 500
        file_list = []
        total_seen = 0
        
        for root, dirs, files in os.walk(base_path):
            # Prune directory search recursively
            dirs[:] = [d for d in dirs if d not in config.EXCLUDE_DIRS]
            
            for file in files:
                if file in config.EXCLUDE_FILES:
                    continue
                
                full_path = Path(root) / file
                rel_path = full_path.relative_to(base_path)
                total_seen += 1
                
                # Check extension filter for source/config files
                if full_path.suffix in config.SUPPORTED_EXTENSIONS or full_path.name in config.SUPPORTED_EXTENSIONS:
                    if len(file_list) < MAX_FILES:
                        file_list.append(str(rel_path).replace("\\", "/"))
        
        result = {"files": file_list, "total_matching": len(file_list)}
        if total_seen > MAX_FILES:
            result["truncated"] = True
            result["note"] = f"File list truncated at {MAX_FILES} files (total matching files: {len(file_list)})"
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def read_file(project_path: str, file_path: str) -> str:
    """
    Safely reads the content of a specific file inside the target project.
    Blocks reading of real environment files (.env) or files containing credentials.
    """
    try:
        base_path = Path(project_path).resolve()
        target_file = (base_path / file_path).resolve()
        
        # Security boundaries check
        if not str(target_file).startswith(str(base_path)):
            return "Error: Access denied. Cannot read files outside the project path."
            
        # Ignore real .env or secret files, but allow reading .env.example
        if target_file.name == ".env" or (target_file.name.startswith(".env") and not target_file.name.endswith(".example")):
            return "Error: Access denied. Real .env/secrets file reading is blocked for security reasons."
            
        if not target_file.exists() or not target_file.is_file():
            return f"Error: File '{file_path}' does not exist or is not a file."
            
        # Check size to prevent reading massive binaries
        if target_file.stat().st_size > 1024 * 1024: # 1MB limit
            return "Error: File is too large to read (limit: 1MB)."
            
        # Read contents
        try:
            content = target_file.read_text(encoding="utf-8", errors="replace")
            return content
        except Exception as e:
            return f"Error reading file content: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def read_directory_tree(project_path: str) -> str:
    """
    Generates a textual hierarchical directory tree structure of the project, skipping ignored folders.
    """
    try:
        base_path = Path(project_path).resolve()
        if not base_path.exists():
            return f"Error: Path '{project_path}' does not exist."
            
        tree_lines = [base_path.name + "/"]
        max_lines = 500
        truncated = False
        
        def build_tree(dir_path: Path, prefix: str = ""):
            nonlocal truncated
            if len(tree_lines) >= max_lines:
                truncated = True
                return
                
            # List directory items, sort them
            try:
                items = sorted(list(dir_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            except Exception:
                return
                
            # Filter ignored items
            filtered_items = []
            for item in items:
                rel = item.relative_to(base_path)
                if item.is_dir():
                    if item.name not in config.EXCLUDE_DIRS:
                        filtered_items.append(item)
                else:
                    if item.name not in config.EXCLUDE_FILES and (item.suffix in config.SUPPORTED_EXTENSIONS or item.name in config.SUPPORTED_EXTENSIONS):
                        filtered_items.append(item)
            
            count = len(filtered_items)
            for i, item in enumerate(filtered_items):
                if len(tree_lines) >= max_lines:
                    truncated = True
                    return
                is_last = (i == count - 1)
                connector = "+-- " if is_last else "|-- "
                
                if item.is_dir():
                    tree_lines.append(f"{prefix}{connector}{item.name}/")
                    new_prefix = prefix + ("    " if is_last else "|   ")
                    build_tree(item, new_prefix)
                else:
                    tree_lines.append(f"{prefix}{connector}{item.name}")
                    
        build_tree(base_path)
        if truncated:
            tree_lines.append(f"... (directory tree truncated at {max_lines} lines)")
        return "\n".join(tree_lines)
    except Exception as e:
        return f"Error building directory tree: {str(e)}"

@mcp.tool()
def search_files_by_pattern(project_path: str, pattern: str) -> str:
    """
    Searches for files matching a glob pattern (e.g., '*.py' or '*package.json') inside the project.
    Returns a JSON list of matching relative file paths.
    """
    try:
        base_path = Path(project_path).resolve()
        if not base_path.exists():
            return json.dumps({"error": f"Path '{project_path}' does not exist."})
            
        matches = []
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in config.EXCLUDE_DIRS]
            
            for file in files:
                if file in config.EXCLUDE_FILES:
                    continue
                
                full_path = Path(root) / file
                rel_path = full_path.relative_to(base_path)
                
                # Check glob pattern
                if fnmatch.fnmatch(file, pattern) or fnmatch.fnmatch(str(rel_path), pattern):
                    matches.append(str(rel_path).replace("\\", "/"))
                    
        return json.dumps({"matches": matches})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def read_configuration_files(project_path: str) -> str:
    """
    Scans for primary project configuration files (e.g. package.json, pyproject.toml, requirements.txt,
    Cargo.toml, go.mod, .env.example) and returns their contents in a structured JSON dictionary.
    """
    try:
        base_path = Path(project_path).resolve()
        if not base_path.exists():
            return json.dumps({"error": f"Path '{project_path}' does not exist."})
            
        config_files = [
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "setup.py",
            "Cargo.toml",
            "go.mod",
            ".env.example",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml"
        ]
        
        results = {}
        for config_file in config_files:
            target = base_path / config_file
            if target.exists() and target.is_file():
                try:
                    # Limit file read size to 100KB for configuration files
                    if target.stat().st_size < 100 * 1024:
                        results[config_file] = target.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    results[config_file] = f"Error reading: {str(e)}"
                    
        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})

log_stderr("All tools registered")

if __name__ == "__main__":
    log_stderr("Entering mcp.run()...")
    mcp.run()
