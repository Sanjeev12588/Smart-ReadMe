# System Architecture Deep-Dive

This document details the software design, agent interaction model, and data flows of the README Copilot application.

---

## 🏛️ High-Level System Architecture

README Copilot decouples user interfaces, AI orchestration, and system interfaces. The CLI interacts with the Google ADK Agents using clean schemas, and the agents interact with the filesystem using the Model Context Protocol (MCP).

```mermaid
graph TD
    User([User]) -->|CLI Command| CLI[Typer CLI / app.py];
    CLI -->|Top-Level Files| Planner(Planner Agent);
    Planner -->|Execution Plan JSON| CLI;
    CLI -->|Dispatched Scan| Analyzer(Project Analyzer Agent);
    Analyzer -->|API Tool Call| Client[LocalMCPClient];
    Client -->|JSON-RPC via Stdio| Server[Local MCP Server];
    Server -->|Read/Write Operations| FS[(Local Filesystem)];
    Server -->|Text Output| Client;
    Client -->|File Data| Analyzer;
    Analyzer -->|Structured Project Profile JSON| CLI;
    CLI -->|Profile + Dir Tree| Generator(README Generator Agent);
    Generator -->|Markdown Output| CLI;
    CLI -->|Save File| Writer[Output Writer];
    Writer -->|Writes README.md| FS;
```

---

## 🤖 Agent Workflow Diagram

This state diagram illustrates the multi-agent execution pipeline. The CLI coordinates execution sequentially to avoid prompt nesting overhead.

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Planner_Active : User supplies project path
    state Planner_Active {
        [*] --> ListFiles
        ListFiles --> GeneratePlan : Gathers top-level files
        GeneratePlan --> PlanReady
    }
    Planner_Active --> Analyzer_Active : CLI receives plan
    state Analyzer_Active {
        [*] --> MapWorkspace : Run list_files tool
        MapWorkspace --> InspectConfigs : Run read_configuration_files
        InspectConfigs --> ExamineSource : Run search/read_file details
        ExamineSource --> CompileJSON : Create Project Profile
    }
    Analyzer_Active --> README_Active : CLI receives tech profile JSON
    state README_Active {
        [*] --> RenderOverview
        RenderOverview --> RenderTechStack
        RenderTechStack --> RenderMermaidFlow
        RenderMermaidFlow --> RenderFinalMD
    }
    README_Active --> Save_Output : Markdown generated
    Save_Output --> [*] : File written successfully
```

---

## ⏱️ System Sequence Diagram

This sequence diagram maps the chronological function calls and message exchanges between components.

```mermaid
sequenceDiagram
    autonumber
    actor User as User CLI
    participant CLI as CLI Orchestrator (app.py)
    participant Planner as Planner Agent (ADK)
    participant Analyzer as Project Analyzer Agent (ADK)
    participant Client as Local MCP Client
    participant Server as Local MCP Server
    participant Generator as README Agent (ADK)
    participant FS as Local Filesystem

    User->>CLI: Run "python app.py [path]"
    CLI->>FS: os.listdir(project_path)
    FS-->>CLI: Return top-level file names
    CLI->>Planner: run_planner(path, files)
    Planner-->>CLI: Return PlannerOutput (JSON Execution Plan)
    CLI->>Client: __aenter__() (Spawn subprocess)
    Client->>Server: Start Server (Stdio)
    Server-->>Client: Handshake complete
    CLI->>Analyzer: run_analyzer(mcp_client)
    loop Codebase Analysis
        Analyzer->>Client: call_tool("list_files")
        Client->>Server: JSON-RPC Call
        Server->>FS: Walk directories
        FS-->>Server: Files list
        Server-->>Client: JSON-RPC Response
        Client-->>Analyzer: Return files list
        Analyzer->>Client: call_tool("read_configuration_files")
        Client->>Server: JSON-RPC Call
        Server->>FS: Read package.json / requirements.txt
        FS-->>Server: Config text
        Server-->>Client: JSON-RPC Response
        Client-->>Analyzer: Return config data
    end
    Analyzer-->>CLI: Return ProjectProfile (JSON Profile)
    CLI->>Client: call_tool("read_directory_tree")
    Client->>Server: JSON-RPC Call
    Server->>FS: Construct tree
    Server-->>Client: Tree text
    Client-->>CLI: Return ASCII directory tree
    CLI->>Client: __aexit__() (Close subprocess)
    Client->>Server: Stop process
    CLI->>Generator: run_readme_generator(profile, tree)
    Generator-->>CLI: Return READMEOutput (Markdown)
    CLI->>FS: Save README.md to project folder
    FS-->>CLI: Save OK
    CLI-->>User: Print Execution Summary Panel
```

---

## 🔌 MCP Data Interaction Diagram

This diagram shows how the filesystem request operations map between the Project Analyzer Agent and the Local MCP Server.

```mermaid
graph LR
    subgraph Agent Domain
        A[Project Analyzer Agent] -->|Call Tool| B[LocalMCPClient]
    end
    subgraph IPC Transport
        B -->|Stdio Write stdin| C[JSON-RPC Stream]
        C -->|Stdio Read stdout| B
    end
    subgraph Server Domain
        C -->|Parse Request| D[FastMCP Server]
        D -->|Safe Path Validation| E{Access Approved?}
        E -->|No| F[Return Access Error]
        E -->|Yes| G[Execute OS Action]
        G -->|Read config / files| H[(Filesystem)]
        H -->|File Content| D
    end
```

---

## ⚙️ Component Responsibilities

### 1. Planner Agent
- **Role**: Coordinates expected steps, expected deliverables, and checklist items.
- **Constraints**: Never reads code contents or writes markdown instructions. Maintains clean sequence task layout.

### 2. Project Analyzer Agent
- **Role**: Dispatches MCP tool calls to inspect configuration settings, language targets, and environment settings.
- **Constraints**: Converts all parameters into a strict Pydantic JSON structure to ensure type safety.

### 3. README Generator Agent
- **Role**: Authors the final documentation.
- **Constraints**: Generates a valid Mermaid sequence or flowchart map representing the target app flow.

### 4. Local MCP Server
- **Role**: Safe broker for disk activities.
- **Constraints**: Excludes folders like `node_modules/` and prevents access to `.env` or credential files.

### 5. CLI & App Orchestrator
- **Role**: Handles Typer parsing, loads environmental `.env` files, starts the MCP subprocess, handles event logs, and saves the output.
- **Constraints**: Renders console warnings and execution details using Rich.
