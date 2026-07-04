import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Gemini Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MODEL = DEFAULT_MODEL  # Backwards-compatible alias — do not use in new code

# Folders and files to exclude from scans
EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "pycache",
    "__pycache__",
    "venv",
    ".venv",
    ".idea",
    ".vscode",
    ".gemini",
    "artifacts",
    "temp_clones",
}

EXCLUDE_FILES = {
    ".DS_Store",
    "thumbs.db",
    "desktop.ini",
}

# Supported file extensions for analysis (code/config files)
SUPPORTED_EXTENSIONS = {
    # Scripts & source
    ".py", ".js", ".jsx", ".ts", ".tsx",
    # Configs & documentation
    ".json", ".toml", ".yaml", ".yml", ".md", ".txt", ".cfg", ".ini",
    # Container & deploy
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    # Scripts
    "package.json", "requirements.txt", "pyproject.toml", "setup.py", "go.mod", "Cargo.toml"
}

def validate_environment():
    """Verify that required API keys are set."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please set it in your environment or a .env file."
        )

def get_resilient_model():
    """Returns a Gemini model instance with retry options for error resilience.
    
    HttpRetryOptions may not be available in all google-genai versions; we
    degrade gracefully to a plain Gemini model if the import fails.
    """
    from google.adk.models.google_llm import Gemini

    try:
        from google.genai.types import HttpRetryOptions
        return Gemini(
            model=DEFAULT_MODEL,
            retry_options=HttpRetryOptions(
                attempts=5,
                initial_delay=2.0,
                max_delay=60.0,
                exp_base=2.0,
                jitter=True,
                http_status_codes=[429, 500, 503, 504]
            )
        )
    except (ImportError, AttributeError, TypeError) as e:
        print(f"[CONFIG] HttpRetryOptions unavailable ({type(e).__name__}: {e}). Using plain Gemini model.")
        return Gemini(model=DEFAULT_MODEL)


def strip_json_fences(text: str) -> str:
    """Strip markdown code fences from Gemini output before JSON parsing.
    
    Gemini sometimes wraps structured output in ```json ... ``` blocks even when
    output_schema is set. This strips those fences so model_validate_json works.
    """
    if not text:
        return text
    stripped = text.strip()
    # Match ```json ... ``` or ``` ... ``` fences
    match = re.match(r"^```(?:json)?\s*\n?([\s\S]*?)\n?```\s*$", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


def format_agent_error(e: Exception) -> str:
    """Analyze agent exception and format a user-friendly error message, especially for quota issues."""
    err_str = str(e)
    is_quota = False
    
    if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "quota" in err_str.lower():
        is_quota = True
        
    if is_quota:
        return (
            f"Error: Quota Exceeded (RESOURCE_EXHAUSTED)\n"
            f"Current model: {DEFAULT_MODEL}\n"
            f"Error type: RESOURCE_EXHAUSTED (429)\n"
            f"Suggested next steps:\n"
            f"  1. Wait for your quota to reset (free tier limits reset daily or per-minute).\n"
            f"  2. Use another Google Gemini Project or API Key with available quota.\n"
            f"  3. Configure a different supported model in your .env file (e.g., 'gemini-2.5-flash-lite')."
        )
    return err_str
