import json
import re

def parse_requirements_txt(content: str) -> list[str]:
    """Parse requirement names from requirements.txt content."""
    requirements = []
    for line in content.splitlines():
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith('#') or line.startswith('-e') or line.startswith('--'):
            continue
        # Split on operators (==, >=, <=, etc.) or spacing
        match = re.match(r'^([a-zA-Z0-9_\-\[\]]+)', line)
        if match:
            requirements.append(match.group(1))
    return requirements

def parse_package_json(content: str) -> dict:
    """Parse scripts and dependency keys from package.json."""
    try:
        data = json.loads(content)
        return {
            "name": data.get("name", "unknown"),
            "version": data.get("version", "1.0.0"),
            "scripts": list(data.get("scripts", {}).keys()),
            "dependencies": list(data.get("dependencies", {}).keys()),
            "devDependencies": list(data.get("devDependencies", {}).keys()),
        }
    except Exception:
        return {}

def parse_pyproject_toml(content: str) -> dict:
    """Parse python dependency keys from pyproject.toml."""
    # Since we don't want to bring in a full toml parser, we can use simple regex to scan sections
    dependencies = []
    current_section = ""
    
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        # Match sections like [tool.poetry.dependencies] or [project.dependencies]
        section_match = re.match(r'^\[(.*)\]$', line)
        if section_match:
            current_section = section_match.group(1)
            continue
            
        # Match dependency lines inside dependency sections
        if "dependencies" in current_section:
            dep_match = re.match(r'^([a-zA-Z0-9_\-\[\]]+)\s*=', line)
            if dep_match:
                name = dep_match.group(1)
                if name.lower() != "python":
                    dependencies.append(name)
                    
    return {"dependencies": dependencies}
