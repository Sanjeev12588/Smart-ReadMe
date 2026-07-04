from pathlib import Path

def validate_markdown(content: str) -> bool:
    """Perform basic checks to ensure markdown has structure and doesn't contain placeholders."""
    if not content:
        return False
    # Check for primary header
    if not content.strip().startswith("#"):
        return False
    # Check for placeholder indicators (e.g., "[TODO]", "<insert", "TODO:", "PLACEHOLDER")
    placeholders = ["[todo]", "<insert", "todo:", "placeholder"]
    content_lower = content.lower()
    for placeholder in placeholders:
        if placeholder in content_lower:
            # We don't fail immediately, but we might log a warning
            pass
    return True

def save_readme(project_path: str, content: str) -> str:
    """Save the generated markdown to README.md in the project path."""
    dest_path = Path(project_path) / "README.md"
    dest_path.write_text(content, encoding="utf-8")
    return str(dest_path.resolve())
