import json
from pathlib import Path

def detect_languages(files: list[str]) -> list[str]:
    """Detect main programming languages in the project from list of files."""
    ext_counts = {}
    for f in files:
        suffix = Path(f).suffix.lower()
        if suffix in ['.py']:
            ext_counts['Python'] = ext_counts.get('Python', 0) + 1
        elif suffix in ['.js', '.jsx']:
            ext_counts['JavaScript'] = ext_counts.get('JavaScript', 0) + 1
        elif suffix in ['.ts', '.tsx']:
            ext_counts['TypeScript'] = ext_counts.get('TypeScript', 0) + 1
            
    # Sort by frequency
    sorted_langs = sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)
    return [lang for lang, count in sorted_langs]

def detect_technologies_from_configs(configs: dict[str, str]) -> dict:
    """Analyze configuration files content to detect frameworks, databases, and tooling."""
    techs = {
        "framework": None,
        "frontend": None,
        "backend": None,
        "database": None,
        "testing_framework": None,
        "package_manager": None,
        "build_system": None
    }
    
    # 1. Python Analysis
    if "requirements.txt" in configs:
        reqs = configs["requirements.txt"].lower()
        if "fastapi" in reqs:
            techs["framework"] = "FastAPI"
            techs["backend"] = "FastAPI"
        elif "django" in reqs:
            techs["framework"] = "Django"
            techs["backend"] = "Django"
        elif "flask" in reqs:
            techs["framework"] = "Flask"
            techs["backend"] = "Flask"
            
        if "pytest" in reqs:
            techs["testing_framework"] = "pytest"
        elif "unittest" in reqs:
            techs["testing_framework"] = "unittest"
            
        if "psycopg2" in reqs or "postgresql" in reqs:
            techs["database"] = "PostgreSQL"
        elif "mysql" in reqs:
            techs["database"] = "MySQL"
        elif "sqlite" in reqs:
            techs["database"] = "SQLite"
        elif "pymongo" in reqs or "motor" in reqs:
            techs["database"] = "MongoDB"
            
        techs["package_manager"] = "pip"
        
    if "pyproject.toml" in configs:
        toml_content = configs["pyproject.toml"].lower()
        if "poetry" in toml_content:
            techs["package_manager"] = "Poetry"
        elif "pipenv" in toml_content:
            techs["package_manager"] = "Pipenv"
            
        if "fastapi" in toml_content:
            techs["framework"] = "FastAPI"
            techs["backend"] = "FastAPI"
        elif "django" in toml_content:
            techs["framework"] = "Django"
            techs["backend"] = "Django"
        elif "flask" in toml_content:
            techs["framework"] = "Flask"
            techs["backend"] = "Flask"
            
        if "pytest" in toml_content:
            techs["testing_framework"] = "pytest"
            
        if "postgresql" in toml_content or "psycopg" in toml_content:
            techs["database"] = "PostgreSQL"
        elif "sqlite" in toml_content:
            techs["database"] = "SQLite"
        elif "mongodb" in toml_content or "pymongo" in toml_content:
            techs["database"] = "MongoDB"
            
    # 2. Node/JS/TS Analysis
    if "package.json" in configs:
        try:
            pkg_data = json.loads(configs["package.json"])
            deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
            deps_lower = {k.lower(): v for k, v in deps.items()}
            
            # Framework/Frontend
            if "next" in deps_lower:
                techs["framework"] = "Next.js"
                techs["frontend"] = "Next.js React"
            elif "react" in deps_lower:
                techs["frontend"] = "React"
                if "express" in deps_lower:
                    techs["framework"] = "Express React"
            
            # Backend
            if "express" in deps_lower:
                techs["backend"] = "Express"
                if not techs["framework"]:
                    techs["framework"] = "Express"
            elif "koa" in deps_lower:
                techs["backend"] = "Koa"
                
            # Database / ORM
            if "prisma" in deps_lower:
                techs["build_system"] = "Prisma ORM"
            if "mongoose" in deps_lower or "mongodb" in deps_lower:
                techs["database"] = "MongoDB"
            elif "pg" in deps_lower or "postgres" in deps_lower:
                techs["database"] = "PostgreSQL"
            elif "mysql2" in deps_lower or "mysql" in deps_lower:
                techs["database"] = "MySQL"
            elif "sqlite3" in deps_lower:
                techs["database"] = "SQLite"
                
            # Testing
            if "jest" in deps_lower:
                techs["testing_framework"] = "Jest"
            elif "mocha" in deps_lower:
                techs["testing_framework"] = "Mocha"
            elif "vitest" in deps_lower:
                techs["testing_framework"] = "Vitest"
                
            # Package Manager / Build System
            # Note: package.json scan defaults to npm/yarn/pnpm
            techs["package_manager"] = "npm" # default, can be verified in client if lockfiles exist
        except Exception:
            pass
            
    # 3. Container Detection
    if "Dockerfile" in configs:
        techs["build_system"] = techs["build_system"] or "Docker"
        
    return techs
