import asyncio
import time
import traceback
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types
import config
from tools.mcp_client import LocalMCPClient

# Timeout for individual MCP tool calls (seconds)
MCP_TOOL_TIMEOUT = 30

class ProjectProfile(BaseModel):
    primary_language: str = Field(description="Main programming language (Python, JavaScript, TypeScript)")
    framework: str = Field(description="Backend/API framework detected (e.g. FastAPI, Express, Flask, Django, etc. or None)")
    frontend_tech: str = Field(description="Frontend technologies (e.g. React, Next.js, HTML/JS, or None)")
    database: str = Field(description="Database system detected (e.g. SQLite, MongoDB, PostgreSQL, etc. or None)")
    package_manager: str = Field(description="Package manager used (e.g. pip, Poetry, npm, yarn, pnpm)")
    entrypoint: str = Field(description="Main application entrypoint path (e.g. app.py, server.js, index.ts)")
    scripts: List[str] = Field(description="Available commands or scripts to build or run the project")
    env_vars: List[str] = Field(description="Environment variables detected from .env.example")
    description: str = Field(description="Description of what this project does")
    files_scanned: int = Field(description="Count of codebase files examined")
    files_ignored: int = Field(description="Count of files bypassed due to exclude rules")
    security_warnings: List[str] = Field(description="Warnings about hardcoded secrets or committed credentials")
    
    # Advanced metadata fields for premium README generation
    screenshots: List[str] = Field(default_factory=list, description="List of detected screenshot or image file paths inside folders like assets, docs, images, screenshots, public.")
    databases: List[str] = Field(default_factory=list, description="List of all detected database systems, e.g. SQLite, MongoDB, PostgreSQL, Redis, DynamoDB, etc.")
    cloud_targets: List[str] = Field(default_factory=list, description="List of detected deployment/cloud targets, e.g. Docker, Vercel, Netlify, Railway, Render, AWS, Azure, GCP, etc.")
    architecture_hints: List[str] = Field(default_factory=list, description="Inferred components of project architecture, e.g. Backend API, React Frontend, Authentication, Workers, Pipelines, Queues, etc.")
    config_details: List[str] = Field(default_factory=list, description="Environment variables or configuration variables parsed from setup/config files with short explanations.")
    api_endpoints: List[str] = Field(default_factory=list, description="Key API endpoints or Swagger/ReDoc URLs detected in the project.")
    inferred_roadmap: List[str] = Field(default_factory=list, description="Roadmap items, future features, or TODO comments inferred from the codebase.")
    contributing_info: str = Field(default="", description="Contribution guidelines or procedures found in files, or empty string.")
    license_info: str = Field(default="", description="Project license type found, e.g. MIT, Apache 2.0, or empty string.")

def get_analyzer_agent(client: LocalMCPClient) -> Agent:
    """Create the Project Analyzer Agent and bind the MCP client tools."""
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "analyzer.md"
    instruction = prompt_path.read_text(encoding="utf-8")
    
    # Define tool functions wrapping the MCP client.
    # Docstrings and parameter type hints are critical for Gemini function calling!
    # Each tool call is wrapped in asyncio.wait_for to prevent infinite hangs.

    async def list_files() -> str:
        """
        Lists all files in the target project path recursively, skipping ignored files.
        """
        try:
            return await asyncio.wait_for(client.list_files(), timeout=MCP_TOOL_TIMEOUT)
        except asyncio.TimeoutError:
            return f"Error: list_files timed out after {MCP_TOOL_TIMEOUT}s"
        
    async def read_file(file_path: str) -> str:
        """
        Reads the content of a specific file inside the target project path.
        Args:
            file_path: The relative path to the file to read.
        """
        try:
            return await asyncio.wait_for(client.read_file(file_path), timeout=MCP_TOOL_TIMEOUT)
        except asyncio.TimeoutError:
            return f"Error: read_file timed out after {MCP_TOOL_TIMEOUT}s"
        
    async def read_directory_tree() -> str:
        """
        Generates a textual hierarchical directory tree structure of the project path.
        """
        try:
            return await asyncio.wait_for(client.read_directory_tree(), timeout=MCP_TOOL_TIMEOUT)
        except asyncio.TimeoutError:
            return f"Error: read_directory_tree timed out after {MCP_TOOL_TIMEOUT}s"
        
    async def search_files_by_pattern(pattern: str) -> str:
        """
        Searches for files matching a glob pattern inside the project path.
        Args:
            pattern: The pattern to match (e.g., '*.py' or 'package.json').
        """
        try:
            return await asyncio.wait_for(client.search_files_by_pattern(pattern), timeout=MCP_TOOL_TIMEOUT)
        except asyncio.TimeoutError:
            return f"Error: search_files_by_pattern timed out after {MCP_TOOL_TIMEOUT}s"
        
    async def read_configuration_files() -> str:
        """
        Scans for primary project configuration files and returns their contents in JSON.
        """
        try:
            return await asyncio.wait_for(client.read_configuration_files(), timeout=MCP_TOOL_TIMEOUT)
        except asyncio.TimeoutError:
            return f"Error: read_configuration_files timed out after {MCP_TOOL_TIMEOUT}s"
        
    return Agent(
        name="analyzer_agent",
        description="Scans project files and configuration to generate a tech profile.",
        model=config.get_resilient_model(),
        instruction=instruction,
        tools=[list_files, read_file, read_directory_tree, search_files_by_pattern, read_configuration_files],
        output_schema=ProjectProfile
    )

async def run_analyzer(client: LocalMCPClient) -> ProjectProfile:
    """Run the Project Analyzer Agent with async tool support."""
    t_start = time.time()
    print(f"[ANALYZER] START — project_path={client.project_path}")

    try:
        agent = get_analyzer_agent(client)
        print(f"[ANALYZER] Agent created — name={agent.name}, model={agent.model}")
    except Exception as e:
        print(f"[ANALYZER] FAILURE — could not create agent: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise
    
    runner = InMemoryRunner(agent=agent)
    runner.auto_create_session = True
    print("[ANALYZER] InMemoryRunner created")
    
    message = (
        f"Please analyze the project at path '{client.project_path}'. "
        "Use your tools to find out: "
        "1. Primary language and framework. "
        "2. Dependencies and databases. "
        "3. Directory structures and env variables. "
        "Output the final results as structured JSON matching the schema."
    )
    
    response_text = ""
    event_count = 0
    print("[ANALYZER] Starting runner.run_async event loop...")

    try:
        async for event in runner.run_async(
            user_id="default_user",
            session_id="analyzer_session",
            new_message=types.Content(parts=[types.Part.from_text(text=message)])
        ):
            event_count += 1
            is_final = event.is_final_response()
            has_content = bool(event.content and event.content.parts)
            part_types = []
            if event.content and event.content.parts:
                part_types = [type(p).__name__ for p in event.content.parts]
            
            # Check if this event carries an error code (e.g. 429 quota exceeded)
            event_error = getattr(event, "error_code", None) or getattr(event, "error", None)
            if event_error:
                print(f"[ANALYZER] Event #{event_count} — ERROR: {event_error}")
            else:
                print(f"[ANALYZER] Event #{event_count} — is_final={is_final}, has_content={has_content}, part_types={part_types}")
            
            if is_final:
                if has_content:
                    # Look for a text part with actual content
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text = part.text
                            print(f"[ANALYZER] Final response captured — length={len(response_text)} chars")
                            break
                    if not response_text:
                        print("[ANALYZER] WARNING — Final response event has parts but no text content")
                else:
                    print("[ANALYZER] WARNING — Final response event has NO content parts at all")
                break
    except Exception as e:
        err_str = str(e)
        print("=" * 60)
        print("[ANALYZER] FAILURE — runner.run_async raised an exception")
        print(f"  EXCEPTION TYPE: {type(e).__name__}")
        print(f"  EXCEPTION MESSAGE: {err_str[:500]}")
        traceback.print_exc()
        print("=" * 60)
        # Re-raise with quota-aware messaging
        if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "quota" in err_str.lower():
            raise RuntimeError(
                f"Analyzer Agent failed: Gemini quota exceeded (429 RESOURCE_EXHAUSTED). "
                "Wait for your quota to reset or switch to a different API key/model."
            ) from e
        raise

    elapsed_agent = round(time.time() - t_start, 2)
    print(f"[ANALYZER] Agent loop finished — total_events={event_count}, got_response={bool(response_text)}, elapsed={elapsed_agent}s")
    
    if not response_text:
        # If the model hit quota, the final event arrives with no content.
        # Provide a specific quota-related error message to help the user.
        quota_hint = "" 
        if event_count > 0:
            quota_hint = (
                " This can happen when Gemini hits a quota limit (429 RESOURCE_EXHAUSTED) "
                "mid-stream. Check your API quota at https://ai.dev/rate-limit and retry after a short wait."
            )
        raise RuntimeError(
            f"Analyzer Agent failed to return a final response after {event_count} events."
            + quota_hint
        )
    
    # Strip markdown fences in case Gemini wraps the JSON in ```json ... ```
    cleaned = config.strip_json_fences(response_text)
    
    print("[ANALYZER] Parsing ProjectProfile from JSON...")
    try:
        result = ProjectProfile.model_validate_json(cleaned)
        elapsed_total = round(time.time() - t_start, 2)
        print(
            f"[ANALYZER] SUCCESS — language={result.primary_language}, "
            f"framework={result.framework}, files_scanned={result.files_scanned}, "
            f"elapsed={elapsed_total}s"
        )
        return result
    except Exception as e:
        print("=" * 60)
        print("[ANALYZER] FAILURE — ProjectProfile.model_validate_json failed")
        print(f"  EXCEPTION TYPE: {type(e).__name__}")
        print(f"  EXCEPTION MESSAGE: {str(e)}")
        print(f"  RAW RESPONSE TEXT (first 3000 chars):\n{response_text[:3000]}")
        traceback.print_exc()
        print("=" * 60)
        raise RuntimeError(f"Analyzer Agent returned invalid JSON: {e}") from e
