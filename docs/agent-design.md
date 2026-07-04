# Agent Design & Prompts

README Copilot implements a multi-agent system using the **Google Agent Development Kit (ADK)**. Instead of a single, long-running monolithic prompt, responsibilities are split among three highly focused agents.

---

## 🤖 Agent 1: Planner Agent

The Planner coordinates project deliverables and defines the scope of analysis. It has **no** access to filesystem tools and **never** writes final documentation. This isolation prevents prompt dilution and maintains architectural focus.

### 📋 Specifications
- **Instructions File**: `prompts/planner.md`
- **Runner Model**: `gemini-2.5-flash`
- **Input Parameters**: Project Path (string), Top-Level Files (list of strings).
- **Structured Output Schema**:
```python
class PlannerOutput(BaseModel):
    project_name: str = Field(description="Detected name of the project")
    steps: List[str] = Field(description="Sequential steps to analyze and document the project")
    expected_deliverables: List[str] = Field(description="Deliverables expected from the analysis")
    validation_rules: List[str] = Field(description="Validation rules for checking the final README")
```

---

## 🔍 Agent 2: Project Analyzer Agent

The Project Analyzer parses config files, reads dependencies, and explores codebase structure using standard tools.

### 📋 Specifications
- **Instructions File**: `prompts/analyzer.md`
- **Runner Model**: `gemini-2.5-flash`
- **Tool Bindings**: List files, Read file, Directory tree, Search files, and Read configuration files.
- **Security Constraint**: Real `.env` or credential reading is hard-blocked at the tool layer.
- **Structured Output Schema**:
```python
class ProjectProfile(BaseModel):
    primary_language: str = Field(description="Main programming language")
    framework: str = Field(description="Backend/API framework detected")
    frontend_tech: str = Field(description="Frontend technologies or None")
    database: str = Field(description="Database system detected or None")
    package_manager: str = Field(description="Package manager used")
    entrypoint: str = Field(description="Main application entrypoint path")
    scripts: List[str] = Field(description="Available commands or scripts to run the project")
    env_vars: List[str] = Field(description="Environment variables detected from .env.example")
    description: str = Field(description="Description of what this project does")
    files_scanned: int = Field(description="Count of files examined")
    files_ignored: int = Field(description="Count of files bypassed due to exclude rules")
    security_warnings: List[str] = Field(description="Warnings about hardcoded secrets")
```

---

## ✍️ Agent 3: README Generator Agent

The README Generator synthesizes the technology profile and directory tree into professional documentation.

### 📋 Specifications
- **Instructions File**: `prompts/readme.md`
- **Runner Model**: `gemini-2.5-flash`
- **Input Parameters**: `ProjectProfile` JSON, Project Directory Tree (string).
- **Quality Rule**: Block placeholders like "TODO" or "[Insert License here]". All contact, installation instructions, and licenses must be generated as complete, production-ready strings.
- **Structured Output Schema**:
```python
class READMEOutput(BaseModel):
    readme_content: str = Field(description="The complete generated Markdown content for the README.md file.")
```

---

## 🧩 Why Structured Outputs are Critical

By using Pydantic models with Google ADK's `output_schema` parameter, the application enforces type safety and structured outputs.

Gemini handles the JSON schema extraction natively at the API level (via `response_schema` configurations in GenAI SDK). This eliminates the need for complex, fragile parsing regexes and guarantees that data passes reliably between the CLI and the agents.
