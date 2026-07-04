# Project Structure Overview

This document describes the folder layout and module design of the README Copilot project. The codebase is organized to separate concerns into specialized directories, ensuring modularity and adherence to SOLID principles.

---

## 📁 Repository Directory Tree

```text
readme-copilot/
│
├── agents/                  # AI Agents (Google ADK)
│   ├── planner_agent.py     # Coordinates task lists and deliverables
│   ├── analyzer_agent.py    # Interfaces with MCP client to scan codebase
│   └── readme_agent.py      # Authors the premium README.md document
│
├── mcp/                     # Model Context Protocol Server
│   └── server.py            # Local FastMCP Server exposing filesystem tools
│
├── prompts/                 # Markdown-based agent system instructions
│   ├── planner.md           # Instructions for Planner Agent
│   ├── analyzer.md          # Instructions for Analyzer Agent
│   └── readme.md            # Instructions for README Generator Agent
│
├── tools/                   # Helper modules and clients
│   ├── detector.py          # Static regex-based technology detection rules
│   ├── parser.py            # Dependency parser for requirements/package configs
│   ├── markdown.py          # Validation and writer wrappers for MD files
│   └── mcp_client.py        # Spawns local MCP server as stdio subprocess
│
├── docs/                    # High-quality documentation assets
│   ├── images/              # Presentation slides and banners
│   └── *.md                 # Architectural and setup guides
│
├── .env.example             # Template file for API key configurations
├── app.py                   # Main CLI entrypoint and orchestrator loop
├── cli.py                   # Visual elements console library (Rich)
├── config.py                # Global settings and folder exclude configs
├── requirements.txt         # Project library dependencies
└── LICENSE                  # MIT open source license file
```

---

## ⚙️ Module Responsibilities

### 1. Agents Layer (`agents/`)
Contains specialized AI personalities built on the **Google Agent Development Kit (ADK)**:
- **Planner Agent**: Generates task checklists based on top-level structures.
- **Analyzer Agent**: Consumes MCP client calls as registered LLM tools.
- **README Agent**: Integrates markdown details and output Mermaid schema flows.

### 2. Protocol Layer (`mcp/`)
Contains the local **Model Context Protocol (MCP)** server built with `FastMCP`. Exposes five core tools (`list_files`, `read_file`, etc.) executing within standard subprocess parameters, decoupling file operations from direct model instructions.

### 3. Prompts Layer (`prompts/`)
System prompts are extracted into standalone `.md` files to keep the code clean. System prompt layouts can be iterated independently without mutating Python scripts.

### 4. Utilities Layer (`tools/`)
Exposes helper methods:
- `mcp_client.py`: Uses an `AsyncExitStack` to manage the subprocess lifecycle of the stdio transport, establishing standard initialization handshake patterns.
- `detector.py`: Resolves languages (Python, JS, TS) and frameworks (FastAPI, React, Django) statically to guide the agent search.
- `parser.py`: Decodes config JSON/TOML keys to extract dependency counts.
- `markdown.py`: Validates headers and saves output file payloads.
