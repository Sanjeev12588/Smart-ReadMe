import asyncio
import time
import traceback
from pathlib import Path
from pydantic import BaseModel, Field
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types
import config
from agents.analyzer_agent import ProjectProfile


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

class READMEOutput(BaseModel):
    readme_content: str = Field(description="The complete generated Markdown content for the README.md file.")

def get_readme_agent() -> Agent:
    """Create and return the README Generator Agent."""
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "readme.md"
    instruction = prompt_path.read_text(encoding="utf-8")
    
    return Agent(
        name="readme_agent",
        description="Generates premium GitHub markdown documentation based on tech profile.",
        model=config.get_resilient_model(),
        instruction=instruction,
        output_schema=READMEOutput
    )

def run_readme_generator(profile: ProjectProfile, directory_tree: str) -> str:
    """Run the README Generator Agent to generate the README content.
    
    IMPORTANT: This function is designed to be called from a background thread
    (via run_in_executor). It creates its own isolated asyncio event loop via
    asyncio.run() to avoid conflicting with FastAPI's running loop.
    """
    t_start = time.time()
    print(f"[README_GEN] START — language={profile.primary_language}, framework={profile.framework}")
    
    try:
        agent = get_readme_agent()
    except Exception as e:
        print(f"[README_GEN] FAILURE — could not create agent: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise

    runner = InMemoryRunner(agent=agent)
    runner.auto_create_session = True
    
    # Construct the instruction input combining structural metadata
    message = (
        f"Project Technical Profile:\n{profile.model_dump_json(indent=2)}\n\n"
        f"Project Directory Tree:\n{directory_tree}"
    )

    # --- Thread-safe event loop strategy ---
    # Called from a ThreadPoolExecutor worker — asyncio.run() creates a fresh,
    # isolated event loop for this thread, completely independent of FastAPI's loop.
    async def _run_agent_async():
        response_text = ""
        event_count = 0
        quota_exceeded = False
        safety_blocked = False
        block_reason = ""
        
        async for event in runner.run_async(
            user_id="default_user",
            session_id="readme_session",
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
            
            print(f"[README_GEN] Event #{event_count} Trace:")
            print(f"  Type: {type(event).__name__}")
            print(f"  Is Final: {is_final}")
            print(f"  Has Content: {has_content} (types={part_types})")
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
                    print(f"[README_GEN] Raw Response Text Captured ({len(response_text)} chars):\n{response_text[:300]}...")
                else:
                    print("[README_GEN] WARNING — Final response has NO content parts")
                break
                
        print(f"[README_GEN] Agent loop done — events={event_count}, got_response={bool(response_text)}")
        
        if quota_exceeded:
            raise RuntimeError("README Generator Agent failed: Gemini API quota limits exceeded (429 Resource Exhausted).")
        if safety_blocked:
            raise RuntimeError(f"README Generator Agent blocked by safety filter: {block_reason}")
            
        return response_text

    try:
        loop = _get_or_create_loop()
        response_text = loop.run_until_complete(_run_agent_async())
    except Exception as e:
        print("=" * 60)
        print("[README_GEN] FAILURE — runner.run_async raised an exception")
        print(f"  EXCEPTION TYPE: {type(e).__name__}")
        print(f"  EXCEPTION MESSAGE: {str(e)}")
        traceback.print_exc()
        print("=" * 60)
        # Preserve specific exceptions raised from _run_agent_async
        if isinstance(e, RuntimeError) and ("quota" in str(e).lower() or "safety" in str(e).lower()):
            raise
        raise RuntimeError(f"README Generator Agent failed during execution: {e}") from e

    if not response_text:
        raise RuntimeError(
            "README Generator Agent failed to return a final response (empty output). "
            "Verify Gemini API status and check that prompt input is valid."
        )
    
    # Strip markdown fences in case Gemini wraps the JSON in ```json ... ```
    cleaned = config.strip_json_fences(response_text)
    
    try:
        output = READMEOutput.model_validate_json(cleaned)
    except Exception as e:
        print("=" * 60)
        print("[README_GEN] FAILURE — JSON parse error")
        print(f"  EXCEPTION TYPE: {type(e).__name__}")
        print(f"  EXCEPTION MESSAGE: {str(e)}")
        print(f"  RAW RESPONSE (first 2000 chars):\n{response_text[:2000]}")
        traceback.print_exc()
        print("=" * 60)
        raise RuntimeError(f"README Generator Agent returned invalid JSON: {e}") from e

    elapsed = round(time.time() - t_start, 2)
    readme_len = len(output.readme_content)
    print(f"[README_GEN] SUCCESS — readme_length={readme_len} chars, elapsed={elapsed}s")
    return output.readme_content
