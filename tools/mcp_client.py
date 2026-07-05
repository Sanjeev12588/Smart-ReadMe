import sys
import asyncio
import time
import traceback
from pathlib import Path
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import os

# Timeout constants (seconds)
MCP_TRANSPORT_TIMEOUT = 180   # How long to wait for the subprocess to start
MCP_HANDSHAKE_TIMEOUT = 180   # How long to wait for the initialize handshake

class LocalMCPClient:
    """
    A client that connects to the local readme-copilot MCP server using stdio transport.
    Exposes clean methods for invoking tools.
    
    Startup timeouts prevent the pipeline from hanging forever if the MCP subprocess
    fails to launch or respond.
    """
    def __init__(self, project_path: str):
        self.project_path = str(Path(project_path).resolve())
        # Locate server.py relative to tools directory
        self.server_path = str(Path(__file__).resolve().parent.parent / "mcp" / "server.py")
        self.exit_stack = AsyncExitStack()
        self.session = None

    async def __aenter__(self):
        t_start = time.time()
        print(f"[MCP_CLIENT] START — connecting to server for project: {self.project_path}")
        print(f"[MCP_CLIENT] Server script: {self.server_path}")
        print(f"[MCP_CLIENT] Python executable: {sys.executable}")

        # Inherit parent environment variables (including PATH and venv settings)
        clean_env = {str(k): str(v) for k, v in os.environ.items()}

        # Configure connection using current Python executable (runs in the venv)
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_path],
            env=clean_env
        )
        
        try:
            # --- Transport connection (subprocess start) ---
            print(f"[MCP_CLIENT] Connecting transport (timeout={MCP_TRANSPORT_TIMEOUT}s)...")
            try:
                read_stream, write_stream = await asyncio.wait_for(
                    self.exit_stack.enter_async_context(stdio_client(server_params)),
                    timeout=MCP_TRANSPORT_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"MCP server subprocess did not start within {MCP_TRANSPORT_TIMEOUT}s. "
                    f"Check that '{self.server_path}' is valid and has no startup errors."
                )
            print("[MCP_CLIENT] Transport connected successfully")

            # --- Session creation ---
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            print(f"[MCP_CLIENT] [{round(time.time() - t_start, 3)}s] Session created, sending initialize handshake request...")

            # --- Initialization handshake ---
            try:
                await asyncio.wait_for(
                    self.session.initialize(),
                    timeout=MCP_HANDSHAKE_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"MCP server did not respond to initialize handshake within {MCP_HANDSHAKE_TIMEOUT}s."
                )
            
            elapsed = round(time.time() - t_start, 2)
            print(f"[MCP_CLIENT] [{elapsed}s] SUCCESS — session initialized and initialize response received!")
            return self

        except Exception as e:
            print("=" * 60)
            print("[MCP_CLIENT] FAILURE — could not connect to MCP server")
            print(f"  EXCEPTION TYPE: {type(e).__name__}")
            print(f"  EXCEPTION MESSAGE: {str(e)}")
            traceback.print_exc()
            print("=" * 60)
            # Clean up any partially-opened resources
            await self.exit_stack.aclose()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print(f"[MCP_CLIENT] Closing session (exc_type={exc_type.__name__ if exc_type else None})")
        try:
            await self.exit_stack.aclose()
            print("[MCP_CLIENT] Session closed successfully")
        except Exception as e:
            print(f"[MCP_CLIENT] Warning — error closing exit_stack: {type(e).__name__}: {e}")

    async def list_files(self) -> str:
        return await self.call_tool("list_files", {})

    async def read_file(self, file_path: str) -> str:
        return await self.call_tool("read_file", {"file_path": file_path})

    async def read_directory_tree(self) -> str:
        return await self.call_tool("read_directory_tree", {})

    async def search_files_by_pattern(self, pattern: str) -> str:
        return await self.call_tool("search_files_by_pattern", {"pattern": pattern})

    async def read_configuration_files(self) -> str:
        return await self.call_tool("read_configuration_files", {})

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a specific tool on the MCP server, injecting project_path automatically.
        
        IMPORTANT: This method now RAISES exceptions instead of returning error strings.
        Returning error strings caused the Analyzer Agent to receive error text as valid
        tool output, leading to JSON parse failures downstream.
        """
        if not self.session:
            raise RuntimeError("MCP Client is not connected. Make sure you use 'async with'.")
            
        # Ensure project_path is always passed to the filesystem tools
        if "project_path" not in arguments:
            arguments["project_path"] = self.project_path
            
        t_start = time.time()
        print(f"[MCP_CLIENT] Calling tool '{tool_name}' with args keys={list(arguments.keys())}")
        
        result = await self.session.call_tool(tool_name, arguments)
        
        elapsed = round(time.time() - t_start, 3)
        
        # Combine text content from all returned parts
        if result and result.content:
            text_parts = []
            for part in result.content:
                if hasattr(part, "text"):
                    text_parts.append(part.text)
            combined = "\n".join(text_parts)
            print(f"[MCP_CLIENT] Tool '{tool_name}' returned {len(combined)} chars in {elapsed}s")
            return combined
        
        print(f"[MCP_CLIENT] Tool '{tool_name}' returned empty content in {elapsed}s")
        return ""
