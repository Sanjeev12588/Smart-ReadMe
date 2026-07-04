# Kaggle Capstone Submission Writeup

## README Copilot: Secure Multi-Agent AI Documentation Assistant
> **Subtitle**: Elevating codebase accessibility using Google ADK, Gemini 2.5 Flash, and the Model Context Protocol.

---

## 📌 Executive Summary
README Copilot is an open-source, CLI-based multi-agent application that automatically generates professional, production-quality GitHub README documentation for any software repository. Developed for the Kaggle AI Agents Intensive Capstone, it demonstrates how **Google ADK** (Agent Development Kit) and the **Model Context Protocol (MCP)** can be coupled to build secure, modular, and type-safe AI workflows.

---

## 1. Problem Statement
Every developer knows the pain of outdated or missing repository documentation. Good documentation is the cornerstone of collaboration, open-source adoption, and clean onboarding. Despite this, writing a comprehensive README is a repetitive chore that is frequently neglected. 

When developers try to solve this using AI, they encounter several critical hurdles:
- **Prompt Overload**: Standard single-prompt LLM wrappers fail on larger projects because they cannot maintain focus across workspace exploration, technology detection, outline planning, and document authoring.
- **Security Vulnerabilities**: Giving an LLM direct filesystem execution capabilities introduces directory traversal risks. Models might accidentally expose real API keys or scan unversioned private variables (`.env`).
- **Malformed Outputs**: AI models often output incomplete placeholders (e.g. `TODO: Add license here`) or break formatting blocks like Mermaid diagrams, rendering them unreadable.

---

## 2. Why AI Agents? (The Shift from Monoliths)
In software engineering, single-function monoliths are anti-patterns. The same applies to prompt engineering. Passing an entire workspace and asking a model to "write a README" results in diluted focus, high hallucination rates, and generic copy.

README Copilot implements an **agentic division of labor**. By isolating concerns into exactly three specialized agents (Planner, Project Analyzer, and README Generator), we create structured boundaries:
- **Planner Agent**: Orchestrates task scopes and validation criteria without writing code.
- **Project Analyzer Agent**: Connects to the local filesystem using secure MCP tools to return a typed JSON tech profile.
- **README Generator Agent**: Compiles the tech profile and tree layout into premium markdown text.

This structured division reduces context window overhead, enforces deterministic data paths, and produces vastly superior documentation.

---

## 3. Technology Stack & Integration

### A. Google ADK (Agent Development Kit)
Google ADK acts as our agent runtime framework. We leverage ADK's `Agent` and `InMemoryRunner` to spin up isolated execution states. 
A key design highlight is our usage of ADK's `output_schema` parameter. By binding Pydantic models directly to agent outputs, ADK instructs the Gemini model to respond in a strict JSON format matching the schema. This guarantees seamless data transfers between agents without regex post-processing.

### B. Google Gemini
We utilize `gemini-2.5-flash` as our core model. Its high speed, low latency, and native function calling capabilities make it ideal for driving interactive CLI utilities. Gemini handles tool call dispatching (function calling) seamlessly when the Analyzer Agent needs to inspect configurations.

### C. Model Context Protocol (MCP)
To solve the filesystem security challenge, we implement the **Model Context Protocol (MCP)** standard. The Project Analyzer Agent does not run Python disk actions. Instead, we host a local `FastMCP` server subprocess inside the CLI. The agent interacts with the codebase *exclusively* through the JSON-RPC interface. This ensures path traversal checks, size caps, and `.env` ignore rules are enforced at the transport layer, completely out of reach of LLM prompt injections.

---

## 4. Architectural Sequence Flow

```text
User CLI Command ──► app.py (Main Controller)
                         │
                         ├──► os.listdir() (Top-level list)
                         ├──► Planner Agent (Generates plan checklist)
                         │
                         ├──► Spawns mcp/server.py (Subprocess stdio)
                         ├──► Project Analyzer Agent (Exposes MCP tools)
                         │        │
                         │        └─── call_tool("read_configuration_files") ──► Filesystem
                         │
                         ├──► README Agent (Takes Profile JSON & drafts README)
                         │
                         └──► Writer (Validates headers & saves file)
```

---

## 5. Implementation Challenges & Solutions

### Challenge 1: Windows Console Unicode Crashes
- *Symptom*: Printing unicode box drawing connectors (`├── `, `└── `) or emojis (`✅`, `✔`) triggered `UnicodeEncodeError` crashes on standard Windows terminal consoles configured to legacy CP1252.
- *Solution*: Rewrote the MCP directory tree builder to output clean ASCII connectors (`|-- ` and `+-- `) and modified the Rich logging styles to use console-safe character arrays (`[+][OK]`).

### Challenge 2: State Tracking & Session Expirations in ADK
- *Symptom*: Running consecutive agent executions triggered `SessionNotFoundError` in ADK's memory manager.
- *Solution*: Configured `runner.auto_create_session = True` on all `InMemoryRunner` instances to dynamically instantiate context states for every execution step.

### Challenge 3: Decoupled Orchestration
- *Symptom*: Nestiing agent calls inside prompts makes debugging hard and increases LLM latency.
- *Solution*: Implemented a clean linear pipeline where the CLI acts as a structured broker, passing typed JSON objects from the Planner to the Analyzer, and finally to the Generator.

---

## 6. Key Results
Running README Copilot on its own codebase demonstrates its efficacy:
- **Duration**: Scans, parses, and writes complete documentation in under 10 seconds.
- **Coverage**: Autodetected Python (Language) and Typer (API framework), ignored `.git/` and `.venv/` directories completely, and mapped out all 16 project modules.
- **Diagrams**: Generated a syntactically correct, readable Mermaid diagram mapping out the orchestrator, agent, and server relationships.

---

## 7. Lessons Learned & Future Directions
- **Tool Isolation works**: Decoupling file actions via MCP is not just a security best practice; it makes testing easier because filesystem mock tools can be run independently of LLM wrappers.
- **Speed-Capability Balance**: Using `gemini-2.5-flash` provides an excellent balance of prompt parsing intelligence, tool dispatching accuracy, and near-instant execution speed.
- **Future Enhancements**: We plan to support remote repository URLs (GitHub/GitLab) and extend static detectors to parse Rust (Cargo), Go (go.mod), and Java (pom.xml) layouts.

---

## 🏁 Conclusion
README Copilot delivers a polished, production-ready implementation of multi-agent collaboration. By utilizing Google ADK for orchestrating agent roles and MCP for securing resource access, the project provides a blueprint for developers building local, developer-centric AI utilities.
