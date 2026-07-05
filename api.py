import os
import re
import sys
import asyncio
import time
import shutil
import tempfile
import subprocess
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent))

import config
from tools.mcp_client import LocalMCPClient
from tools.markdown import validate_markdown, save_readme
from agents.planner_agent import run_planner
from agents.analyzer_agent import run_analyzer
from agents.readme_agent import run_readme_generator

# ─────────────────────────────────────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="README Copilot API",
    description="Backend API for the README Copilot multi-agent AI documentation generator",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_URL_PATTERN = re.compile(
    r"^https?://(www\.)?github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?/?$",
    re.IGNORECASE
)

# Overall pipeline timeout in seconds. If the full generation flow exceeds this,
# the client receives a 504 instead of hanging until the browser closes the connection.
PIPELINE_TIMEOUT_SECONDS = 300  # 5 minutes

# Git clone timeout in seconds
GIT_CLONE_TIMEOUT_SECONDS = 120  # 2 minutes

# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    project_path: Optional[str] = Field(None, description="Local project path on the system")
    github_url: Optional[str] = Field(None, description="Public GitHub repository HTTP URL")
    github_mode: Optional[bool] = Field(None, description="Explicitly request GitHub mode over local path")

class TechProfileData(BaseModel):
    primary_language: str
    framework: str
    frontend_tech: str
    database: str
    package_manager: str
    files_scanned: int
    files_ignored: int
    project_type: str = Field("Other", description="Classified repository type")

class GenerateResponse(BaseModel):
    success: bool
    readme_content: str
    project_name: str
    tech_profile: TechProfileData
    execution_time: float
    saved_path: Optional[str] = None

# ─────────────────────────────────────────────────────────────────────────────
# Git Clone Helper
# ─────────────────────────────────────────────────────────────────────────────

def clone_github_repo(url: str, dest_dir: str) -> None:
    """Clone a public GitHub repository to a local directory.
    
    Uses --depth 1 (shallow clone) for speed.
    Enforces a timeout to prevent indefinite hangs on large or slow repos.
    """
    print(f"[GIT_CLONE] START — url={url}, dest={dest_dir}")
    t_start = time.time()
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, dest_dir],
            capture_output=True,
            text=True,
            check=True,
            timeout=GIT_CLONE_TIMEOUT_SECONDS
        )
        elapsed = round(time.time() - t_start, 2)
        print(f"[GIT_CLONE] SUCCESS — elapsed={elapsed}s")
    except subprocess.TimeoutExpired:
        raise ValueError(
            f"Git clone timed out after {GIT_CLONE_TIMEOUT_SECONDS}s. "
            "The repository may be too large or the network is slow."
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        raise ValueError(f"Git clone failed: {error_msg.strip()}")
    except FileNotFoundError:
        raise ValueError(
            "Git client is not installed on this system. "
            "Install Git from https://git-scm.com/downloads"
        )

# ─────────────────────────────────────────────────────────────────────────────
# Thread Pool for Synchronous ADK Agents
# ─────────────────────────────────────────────────────────────────────────────

# Planner and README agents are offloaded to a dedicated thread pool.
# Each worker thread gets a persistent (never-closed) event loop stored in
# thread-local storage. This avoids two problems:
#   1. asyncio.run() would close the loop after each call, causing Google GenAI's
#      httpx cleanup coroutines to log "RuntimeError: Event loop is closed".
#   2. Using the FastAPI event loop from a thread would raise
#      "RuntimeError: This event loop is already running".
import threading
_thread_local = threading.local()

def _get_thread_loop() -> asyncio.AbstractEventLoop:
    """Get or create a persistent event loop for the current executor thread."""
    loop = getattr(_thread_local, "loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _thread_local.loop = loop
    return loop

_AGENT_THREAD_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="adk_agent")

# ─────────────────────────────────────────────────────────────────────────────
# Generation Flow
# ─────────────────────────────────────────────────────────────────────────────

async def execute_generation_flow(target_path: str) -> tuple[str, str, TechProfileData]:
    """Execute the multi-agent orchestration steps to construct the README.
    
    Pipeline:
      1. Scan top-level files → bootstrap planner
      2. Run Planner Agent (thread pool — uses asyncio.run internally)
      3. Connect MCP Client → Run Analyzer Agent (async, on FastAPI loop)
      4. Run README Generator Agent (thread pool — uses asyncio.run internally)
      5. Validate markdown output
    """
    resolved_path = str(Path(target_path).resolve())
    
    # 0. Validate and scan top-level files to bootstrap the planner
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"Target path does not exist: {resolved_path}")
    if not os.path.isdir(resolved_path):
        raise ValueError(f"Target path is not a directory: {resolved_path}")
        
    top_level_files = [
        item for item in os.listdir(resolved_path)
        if item not in config.EXCLUDE_DIRS
    ]
    print(f"[PIPELINE] Top-level files scanned: {len(top_level_files)}")

    # FIX: Use get_running_loop() instead of the deprecated get_event_loop().
    # Inside an async function, get_running_loop() always returns the active loop.
    # get_event_loop() can return a closed or wrong loop in Python 3.10+.
    loop = asyncio.get_running_loop()

    # 1. Planner Agent — runs in executor thread with its own asyncio.run() loop
    print("[PIPELINE] STEP 1 — Planner Agent starting...")
    t_planner = time.time()
    plan = await loop.run_in_executor(
        _AGENT_THREAD_POOL,
        lambda: run_planner(resolved_path, top_level_files)
    )
    print(f"[PIPELINE] STEP 1 — Planner done in {round(time.time()-t_planner,2)}s, project_name='{plan.project_name}'")
    
    # 2. Analyzer Agent — runs async on the FastAPI event loop, uses MCP client
    print("[PIPELINE] STEP 2 — MCP Client + Analyzer Agent starting...")
    t_analyzer = time.time()
    async with LocalMCPClient(resolved_path) as mcp_client:
        profile = await run_analyzer(mcp_client)
        directory_tree = await mcp_client.read_directory_tree()
    print(f"[PIPELINE] STEP 2 — Analyzer done in {round(time.time()-t_analyzer,2)}s")
    
    # 3. README Generator — runs in executor thread with its own asyncio.run() loop
    print("[PIPELINE] STEP 3 — README Generator starting...")
    t_readme = time.time()
    readme_content = await loop.run_in_executor(
        _AGENT_THREAD_POOL,
        lambda: run_readme_generator(profile, directory_tree)
    )
    print(f"[PIPELINE] STEP 3 — README Generator done in {round(time.time()-t_readme,2)}s, length={len(readme_content)} chars")
    
    # 4. Basic validation check
    print("[PIPELINE] STEP 4 — Validating README output...")
    if not validate_markdown(readme_content):
        print("[PIPELINE] WARNING — README validation returned False (missing header or empty)")

    tech_profile = TechProfileData(
        primary_language=profile.primary_language,
        framework=profile.framework,
        frontend_tech=profile.frontend_tech,
        database=profile.database,
        package_manager=profile.package_manager,
        files_scanned=profile.files_scanned,
        files_ignored=profile.files_ignored,
        project_type=profile.project_type
    )
    return readme_content, plan.project_name, tech_profile

# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/generate", response_model=GenerateResponse)
async def generate_readme(request: GenerateRequest):
    """
    Main API endpoint to generate a README.md.
    Supports either local filepaths or public GitHub repository URLs.
    
    Returns HTTP 504 if the pipeline exceeds PIPELINE_TIMEOUT_SECONDS.
    Returns HTTP 400 for invalid inputs.
    Returns HTTP 500 for internal agent failures with full error detail.
    """
    current_stage = "validate_request"
    print(f"[API] ========== NEW REQUEST — stage={current_stage} ==========")

    # Validate environment first
    try:
        config.validate_environment()
    except ValueError as e:
        print(f"[API] FAILURE — environment validation: {e}")
        raise HTTPException(status_code=500, detail=f"API Setup error: {str(e)}")

    # 1. Normalize inputs
    project_path = (request.project_path or "").strip() or None
    github_url = (request.github_url or "").strip() or None
    github_mode = bool(request.github_mode)

    # 2. Ensure at least one parameter is provided
    if not project_path and not github_url:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'project_path' or 'github_url' in the request body."
        )

    # 3. Determine mode
    use_github = False
    if project_path and github_url:
        use_github = github_mode
    elif github_url:
        use_github = True

    # 4. Validate GitHub URL format
    if use_github:
        if not GITHUB_URL_PATTERN.match(github_url):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid GitHub URL. Must be a valid public GitHub repository URL. "
                    "Example: https://github.com/user/repo"
                )
            )

    start_time = time.time()
    temp_dir = None
    
    try:
        # 5a. Clone GitHub repo or use local path
        if use_github:
            current_stage = "git_clone"
            print(f"[API] Stage: {current_stage} — url={github_url}")
            base_temp_path = Path(__file__).resolve().parent / "temp_clones"
            base_temp_path.mkdir(exist_ok=True)
            temp_dir = tempfile.mkdtemp(dir=str(base_temp_path), prefix="git_clone_")
            
            clone_github_repo(github_url, temp_dir)
            target_path = temp_dir
        else:
            current_stage = "validate_local_path"
            print(f"[API] Stage: {current_stage} — path={project_path}")
            if not os.path.exists(project_path) or not os.path.isdir(project_path):
                raise HTTPException(
                    status_code=400,
                    detail=f"Path '{project_path}' is not a valid directory."
                )
            target_path = project_path

        # 6. Execute the generation flow with an overall pipeline timeout.
        # If the pipeline exceeds PIPELINE_TIMEOUT_SECONDS, the client gets HTTP 504
        # instead of "Failed to fetch" from a browser-level TCP timeout.
        current_stage = "execute_pipeline"
        print(f"[API] Stage: {current_stage} — target_path={target_path}")
        print(f"[API] Pipeline timeout: {PIPELINE_TIMEOUT_SECONDS}s")
        
        try:
            readme_content, project_name, tech_profile = await asyncio.wait_for(
                execute_generation_flow(target_path),
                timeout=PIPELINE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail=(
                    f"The README generation pipeline timed out after {PIPELINE_TIMEOUT_SECONDS}s. "
                    "The repository may be too large or the AI model is under heavy load. "
                    "Please try again or use a smaller repository."
                )
            )
        
        # 7. Save file locally if running against a local project path
        current_stage = "save_readme"
        saved_path = None
        if not use_github:
            saved_path = save_readme(target_path, readme_content)
            print(f"[API] README saved to: {saved_path}")
            
        duration = round(time.time() - start_time, 2)
        print(f"[API] ========== REQUEST COMPLETE — elapsed={duration}s, project='{project_name}' ==========")
        
        return GenerateResponse(
            success=True,
            readme_content=readme_content,
            project_name=project_name,
            tech_profile=tech_profile,
            execution_time=duration,
            saved_path=saved_path
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is (they are already properly formatted)
        raise

    except ValueError as e:
        print("=" * 60)
        print(f"[API] FAILURE (ValueError) — stage={current_stage}")
        print(f"  MESSAGE: {str(e)}")
        traceback.print_exc()
        print("=" * 60)
        raise HTTPException(status_code=400, detail=str(e))

    except FileNotFoundError as e:
        print("=" * 60)
        print(f"[API] FAILURE (FileNotFoundError) — stage={current_stage}")
        print(f"  MESSAGE: {str(e)}")
        traceback.print_exc()
        print("=" * 60)
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        print("=" * 60)
        print(f"[API] FAILURE (Unhandled Exception) — stage={current_stage}")
        print(f"  EXCEPTION TYPE: {type(e).__name__}")
        print(f"  EXCEPTION MESSAGE: {str(e)}")
        traceback.print_exc()
        print("=" * 60)
        # Use format_agent_error to provide quota-aware messaging
        raise HTTPException(status_code=500, detail=config.format_agent_error(e))
        
    finally:
        # Always clean up temporary clone directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"[API] Cleaned up temp_dir: {temp_dir}")
            except Exception as cleanup_err:
                print(f"[API] Warning — could not clean up temp_dir: {cleanup_err}")


@app.get("/api/health")
async def health_check():
    """Simple API status health endpoint."""
    return {
        "status": "healthy",
        "model": config.DEFAULT_MODEL,
        "api_key_set": bool(config.GEMINI_API_KEY),
        "pipeline_timeout_seconds": PIPELINE_TIMEOUT_SECONDS
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8050, reload=True)
