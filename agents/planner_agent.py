import asyncio
import time
import traceback
import sys
import os
from pathlib import Path
# Add project root to sys.path so we can import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pydantic import BaseModel, Field
from typing import List
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types
import config


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    """Get or create a persistent event loop for the current executor thread.
    
    Using a persistent loop (rather than asyncio.run which closes after each call)
    prevents 'RuntimeError: Event loop is closed' from Google GenAI's httpx cleanup.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop is closed")
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

class PlannerOutput(BaseModel):
    project_name: str = Field(description="Detected name of the project")
    steps: List[str] = Field(description="Sequential steps to analyze and document the project")
    expected_deliverables: List[str] = Field(description="Deliverables expected from the analysis")
    validation_rules: List[str] = Field(description="Validation rules for checking the final README")

def get_planner_agent() -> Agent:
    """Create and return the Planner Agent instance."""
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "planner.md"
    instruction = prompt_path.read_text(encoding="utf-8")
    
    return Agent(
        name="planner_agent",
        description="Coordinates documentation plan and tasks.",
        model=config.get_resilient_model(),
        instruction=instruction,
        output_schema=PlannerOutput
    )

def run_planner(project_path: str, top_level_files: List[str]) -> PlannerOutput:
    """Run the Planner Agent to generate the execution plan.
    
    IMPORTANT: This function is designed to be called from a background thread
    (via run_in_executor). It creates its own isolated asyncio event loop via
    asyncio.run() to avoid conflicting with FastAPI's running loop.
    """
    t_start = time.time()
    print(f"[PLANNER] START — project_path={project_path}")
    
    try:
        agent = get_planner_agent()
    except Exception as e:
        print(f"[PLANNER] FAILURE — could not create agent: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

    runner = InMemoryRunner(agent=agent)
    runner.auto_create_session = True
    
    # Construct prompt message containing project path and file list
    message = (
        f"Project Path: {project_path}\n"
        f"Top-level files: {top_level_files}"
    )

    # --- Thread-safe event loop strategy ---
    # We are running inside a ThreadPoolExecutor worker, so no event loop exists
    # on this thread yet. asyncio.run() creates a brand new loop, runs the coroutine
    # to completion, then closes it — completely isolated from FastAPI's loop.
    async def _run_agent_async():
        response_text = ""
        event_count = 0
        quota_exceeded = False
        safety_blocked = False
        block_reason = ""
        
        async for event in runner.run_async(
            user_id="default_user",
            session_id="planner_session",
            new_message=types.Content(parts=[types.Part.from_text(text=message)])
        ):
            event_count += 1
            is_final = event.is_final_response()
            has_content = bool(event.content and event.content.parts)
            
            # Trace event details
            part_types = []
            if event.content and event.content.parts:
                part_types = [type(p).__name__ for p in event.content.parts]
            
            finish_reason = getattr(event, "finish_reason", None)
            error_code = getattr(event, "error_code", None)
            error_message = getattr(event, "error_message", None)
            usage_metadata = getattr(event, "usage_metadata", None)
            func_calls = event.get_function_calls() if hasattr(event, "get_function_calls") else []
            func_responses = event.get_function_responses() if hasattr(event, "get_function_responses") else []
            
            print(f"[PLANNER] Event #{event_count} Trace:")
            print(f"  Type: {type(event).__name__}")
            print(f"  Is Final: {is_final}")
            print(f"  Has Content: {has_content} (types={part_types})")
            print(f"  Function Calls: {len(func_calls)}")
            print(f"  Function Responses: {len(func_responses)}")
            print(f"  Finish Reason: {finish_reason}")
            print(f"  Error Code: {error_code}")
            print(f"  Error Message: {error_message}")
            if usage_metadata:
                print(f"  Usage: prompt={usage_metadata.prompt_token_count}, candidates={usage_metadata.candidates_token_count}, total={usage_metadata.total_token_count}")
            
            # Detect quota / safety limits
            if error_code == "RESOURCE_EXHAUSTED" or (error_message and "429" in error_message):
                quota_exceeded = True
            if finish_reason == types.FinishReason.SAFETY or error_code == "SAFETY":
                safety_blocked = True
                block_reason = error_message or "Content generation blocked by safety filters."
            elif finish_reason == types.FinishReason.RECITATION:
                safety_blocked = True
                block_reason = "Generation stopped due to recitation/citation flags."
            
            if is_final:
                if has_content:
                    parts_text = []
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            parts_text.append(part.text)
                    response_text = "".join(parts_text)
                    print(f"[PLANNER] Raw Response Text Captured ({len(response_text)} chars):\n{response_text}")
                else:
                    print("[PLANNER] WARNING: Final event contains no content parts.")
                break
                
        print(f"[PLANNER] Agent loop done — events={event_count}, got_response={bool(response_text)}")
        
        if quota_exceeded:
            raise RuntimeError("Planner Agent failed: Gemini API quota limits exceeded (429 Resource Exhausted).")
        if safety_blocked:
            raise RuntimeError(f"Planner Agent blocked by safety filter: {block_reason}")
            
        return response_text

    try:
        loop = _get_or_create_loop()
        response_text = loop.run_until_complete(_run_agent_async())
    except Exception as e:
        print("=" * 60)
        print("[PLANNER] FAILURE — runner.run_async raised an exception")
        print(f"  EXCEPTION TYPE: {type(e).__name__}")
        print(f"  EXCEPTION MESSAGE: {str(e)}")
        traceback.print_exc()
        print("=" * 60)
        # Preserve specific exceptions raised from _run_agent_async
        if isinstance(e, RuntimeError) and ("quota" in str(e).lower() or "safety" in str(e).lower()):
            raise
        raise RuntimeError(f"Planner Agent failed during execution: {e}") from e

    if not response_text:
        raise RuntimeError(
            "Planner Agent failed to return a final response (empty output). "
            "Verify Gemini API status and check that prompt input is valid."
        )
    
    # Strip markdown fences in case Gemini wraps the JSON in ```json ... ```
    cleaned = config.strip_json_fences(response_text)
    
    try:
        result = PlannerOutput.model_validate_json(cleaned)
    except Exception as e:
        print("=" * 60)
        print("[PLANNER] FAILURE — JSON parse error")
        print(f"  EXCEPTION TYPE: {type(e).__name__}")
        print(f"  EXCEPTION MESSAGE: {str(e)}")
        print(f"  RAW RESPONSE (first 2000 chars):\n{response_text[:2000]}")
        traceback.print_exc()
        print("=" * 60)
        raise RuntimeError(f"Planner Agent returned invalid JSON: {e}") from e

    elapsed = round(time.time() - t_start, 2)
    print(f"[PLANNER] SUCCESS — project_name='{result.project_name}', steps={len(result.steps)}, elapsed={elapsed}s")
    return result
