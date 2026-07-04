# Model Context Protocol (MCP) Integration

README Copilot implements a secure file operations layer using the **Model Context Protocol (MCP)**. This separates filesystem interactions from LLM planning, ensuring security boundaries are enforced.

---

## 🔌 MCP Architecture

The Project Analyzer Agent does **not** make direct Python filesystem calls (`os.walk`, `open().read()`). Instead, it communicates with an isolated local MCP server.

```text
  [ Project Analyzer Agent ]
              │
              ▼ (Exposes LLM Tools)
     [ LocalMCPClient ]
              │
              ▼ (Communicates via stdin/stdout json-rpc)
     [ Local MCP Server (server.py) ]
              │
              ▼ (Direct OS actions with safety guards)
        [ Filesystem ]
```

---

## 🛠️ MCP Filesystem Tools

The local MCP server is implemented in `mcp/server.py` using `FastMCP`. It registers five filesystem tools:

### 1. `list_files`
- **Arguments**: `project_path: str`
- **Behavior**: Recursively lists all supported source and config files.
- **Safety**: Bypasses any directories or files declared in `config.EXCLUDE_DIRS` and `config.EXCLUDE_FILES`.

### 2. `read_file`
- **Arguments**: `project_path: str`, `file_path: str`
- **Behavior**: Safely reads file text (max 1MB).
- **Safety**: Blocks path traversal (denies reading files outside the project path). Bypasses real `.env` or credential files (e.g. `.pem`), returning security error messages.

### 3. `read_directory_tree`
- **Arguments**: `project_path: str`
- **Behavior**: Renders a complete repository map using stable ASCII lines (`+--` and `|--`).
- **Safety**: Excludes ignored folders like `.git/` or `node_modules/`.

### 4. `search_files_by_pattern`
- **Arguments**: `project_path: str`, `pattern: str`
- **Behavior**: Scans file lists using glob matching.

### 5. `read_configuration_files`
- **Arguments**: `project_path: str`
- **Behavior**: Automatically reads common configuration templates (`package.json`, `requirements.txt`, `.env.example`, etc.) in a single batch read operation.

---

## 🚇 Stdio Subprocess Transport

The client wrapper in `tools/mcp_client.py` uses the standard Python `mcp` library to orchestrate connection lifecycles:

1. **Subprocess Spawn**: Uses `sys.executable` (routing to the current virtual environment's Python binary) to run `mcp/server.py` in a background subprocess.
2. **Handshake**: Communicates using `stdio_client` and `ClientSession` to run the standard MCP initialization handshake.
3. **Execution Routing**: Wraps JSON-RPC requests via `session.call_tool` and resolves returned `CallToolResult` text parts into formatted strings.
4. **Subprocess Teardown**: Uses an `AsyncExitStack` context manager to clean up the subprocess pipes and resources.
