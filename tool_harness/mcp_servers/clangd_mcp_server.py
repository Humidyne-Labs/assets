#!/usr/bin/env python3
"""
Clangd LSP Bridge MCP Server.
Bridges LLM agents to the clangd Language Server Protocol (LSP) for deep C/C++ semantic analysis:
- Definition & declaration lookup
- Reference searching across projects
- Hover documentation, type signatures, and macro expansions
- Workspace & document symbol outline search
- Compiler diagnostics (errors, warnings, notes)
"""

import sys
import logging
import os
import json
import time
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

# Oversight File & Stream Logging Setup
LOG_DIR = Path.home() / ".mcp_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "clangd_mcp_server.log"

class SuppressRPCValidationErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "Failed to validate request" in msg or "validation errors for ClientRequest" in msg:
            return False
        return True

_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"))

_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"))

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
_root_logger.handlers = [_file_handler, _stderr_handler]
_root_logger.addFilter(SuppressRPCValidationErrorFilter())

logger = logging.getLogger("clangd_mcp")

mcp = FastMCP("Clangd-LSP-Server")

# Configuration Defaults
DEFAULT_CLANGD_BIN = os.environ.get("CLANGD_PATH", r"C:\clang+llvm-18.1.8\bin\clangd.exe")
DEFAULT_WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp")).resolve()


class ClangdLSPClient:
    """Manages child clangd process and JSON-RPC framing over stdio."""

    def __init__(self, clangd_bin: str, workspace_root: Path, compile_commands_dir: Optional[Path] = None):
        self.clangd_bin = clangd_bin
        self.workspace_root = workspace_root
        self.compile_commands_dir = compile_commands_dir or self._discover_compile_commands(workspace_root)
        self.process: Optional[subprocess.Popen] = None
        self._req_id = 0
        self._lock = threading.Lock()
        self._pending_requests: Dict[int, Dict[str, Any]] = {}
        self._diagnostics: Dict[str, List[Dict[str, Any]]] = {}
        self._open_documents: set[str] = set()
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False

    def _discover_compile_commands(self, root: Path) -> Optional[Path]:
        """Search common ESP-IDF build directories for compile_commands.json."""
        candidates = [
            root / "examples" / "Unified_Environmental_Demo" / "build_dev",
            root / "examples" / "Unified_Environmental_Demo" / "build",
            root / "examples" / "Peripherals_Test_Suite" / "build_dev",
            root / "examples" / "Peripherals_Test_Suite" / "build",
            root / "build_dev",
            root / "build",
        ]
        for c in candidates:
            if (c / "compile_commands.json").exists():
                logger.info(f"Auto-discovered compile_commands.json at: {c}")
                return c
        return None

    def start(self):
        """Spawn clangd subprocess and perform LSP handshake."""
        with self._lock:
            if self.process and self.process.poll() is None:
                return

            cmd = [
                self.clangd_bin,
                "--background-index",
                "--header-insertion=never",
                "--completion-style=detailed",
                "--query-driver=**",
            ]
            if self.compile_commands_dir and self.compile_commands_dir.exists():
                cmd.append(f"--compile-commands-dir={self.compile_commands_dir}")

            logger.info(f"Starting clangd process: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
            self._running = True

            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()

            # stderr logging thread
            threading.Thread(target=self._stderr_loop, daemon=True).start()

        # Perform LSP initialize handshake
        init_res = self._send_request("initialize", {
            "processId": os.getpid(),
            "rootUri": self.workspace_root.as_uri(),
            "capabilities": {
                "textDocument": {
                    "hover": {"contentFormat": ["plaintext", "markdown"]},
                    "definition": {"linkSupport": True},
                    "references": {},
                    "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                    "publishDiagnostics": {}
                },
                "workspace": {
                    "symbol": {}
                }
            },
            "initializationOptions": {
                "compilationDatabasePath": str(self.compile_commands_dir) if self.compile_commands_dir else ""
            }
        })
        logger.info(f"clangd initialized: {init_res.get('serverInfo', {})}")
        self._send_notification("initialized", {})

    def _stderr_loop(self):
        """Read clangd stderr for logs."""
        try:
            while self._running and self.process and self.process.stderr:
                line = self.process.stderr.readline()
                if not line:
                    break
                logger.debug(f"[clangd stderr] {line.decode('utf-8', errors='replace').rstrip()}")
        except Exception as e:
            logger.debug(f"stderr reader error: {e}")

    def _reader_loop(self):
        """Read stdout, parse Content-Length headers, and dispatch JSON-RPC messages."""
        stdout = self.process.stdout
        while self._running and stdout:
            try:
                # 1. Read headers until \r\n\r\n
                content_length = 0
                while True:
                    line = stdout.readline()
                    if not line:
                        logger.warning("clangd stdout EOF reached")
                        return
                    line_str = line.decode("ascii", errors="replace").strip()
                    if not line_str:
                        # Empty line marks end of headers
                        break
                    if line_str.lower().startswith("content-length:"):
                        content_length = int(line_str.split(":", 1)[1].strip())

                if content_length <= 0:
                    continue

                # 2. Read exact payload body
                body = stdout.read(content_length)
                if not body:
                    break

                msg = json.loads(body.decode("utf-8", errors="replace"))

                # 3. Handle Responses vs Notifications
                if "id" in msg and msg["id"] in self._pending_requests:
                    req_id = msg["id"]
                    entry = self._pending_requests[req_id]
                    entry["response"] = msg
                    entry["event"].set()
                elif "method" in msg:
                    method = msg["method"]
                    params = msg.get("params", {})
                    if method == "textDocument/publishDiagnostics":
                        uri = params.get("uri", "")
                        diags = params.get("diagnostics", [])
                        self._diagnostics[uri] = diags
            except Exception as e:
                logger.error(f"Error in LSP reader loop: {e}")
                time.sleep(0.05)

    def _send_request(self, method: str, params: Any, timeout_sec: float = 8.0) -> Dict[str, Any]:
        """Send JSON-RPC request and wait synchronously for response."""
        self.start()
        with self._lock:
            self._req_id += 1
            req_id = self._req_id
            event = threading.Event()
            self._pending_requests[req_id] = {"event": event, "response": None}

            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params,
            }
            data = json.dumps(payload).encode("utf-8")
            header = f"Content-Length: {len(data)}\r\n\r\n".encode("ascii")
            self.process.stdin.write(header + data)
            self.process.stdin.flush()

        if not event.wait(timeout=timeout_sec):
            with self._lock:
                self._pending_requests.pop(req_id, None)
            raise TimeoutError(f"Request {method} (id={req_id}) timed out after {timeout_sec}s")

        with self._lock:
            entry = self._pending_requests.pop(req_id, {})
        resp = entry.get("response", {})
        if "error" in resp:
            raise RuntimeError(f"LSP error for {method}: {resp['error']}")
        return resp.get("result")

    def _send_notification(self, method: str, params: Any):
        """Send asynchronous JSON-RPC notification (no response expected)."""
        self.start()
        with self._lock:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
            data = json.dumps(payload).encode("utf-8")
            header = f"Content-Length: {len(data)}\r\n\r\n".encode("ascii")
            self.process.stdin.write(header + data)
            self.process.stdin.flush()

    def open_document_if_needed(self, file_path: Path):
        """Ensure file is opened in clangd session for live indexing."""
        uri = file_path.as_uri()
        if uri not in self._open_documents and file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                ext = file_path.suffix.lower()
                lang_id = "cpp" if ext in (".cpp", ".hpp", ".cc", ".cxx") else "c"
                self._send_notification("textDocument/didOpen", {
                    "textDocument": {
                        "uri": uri,
                        "languageId": lang_id,
                        "version": 1,
                        "text": content
                    }
                })
                self._open_documents.add(uri)
            except Exception as e:
                logger.warning(f"Failed to open document {file_path}: {e}")

    def get_diagnostics_for_uri(self, uri: str) -> List[Dict[str, Any]]:
        return self._diagnostics.get(uri, [])


# Global LSP Client Instance
_lsp_client = ClangdLSPClient(DEFAULT_CLANGD_BIN, DEFAULT_WORKSPACE_ROOT)


def _resolve_file(file_path_str: str) -> Path:
    p = Path(file_path_str)
    if not p.is_absolute():
        p = (DEFAULT_WORKSPACE_ROOT / p).resolve()
    return p


# =========================================================================
# MCP Tools Exposure
# =========================================================================

@mcp.tool()
def clangd_get_definition(file_path: str, line: int, character: int) -> str:
    """
    Jump to the definition or declaration of a C/C++ symbol.

    Args:
        file_path: Absolute or workspace-relative path to the source/header file.
        line: 1-indexed line number of the symbol.
        character: 1-indexed column/character position of the symbol.
    """
    p = _resolve_file(file_path)
    if not p.exists():
        return f"Error: File not found: {p}"

    _lsp_client.open_document_if_needed(p)
    try:
        res = _lsp_client._send_request("textDocument/definition", {
            "textDocument": {"uri": p.as_uri()},
            "position": {"line": max(0, line - 1), "character": max(0, character - 1)}
        })
        if not res:
            return "No definition found at specified location."

        results = []
        items = res if isinstance(res, list) else [res]
        for item in items:
            # Handle Location or LocationLink
            uri = item.get("uri") or item.get("targetUri", "")
            target_range = item.get("range") or item.get("targetSelectionRange", {})
            start = target_range.get("start", {})
            tgt_line = start.get("line", 0) + 1
            tgt_col = start.get("character", 0) + 1
            clean_path = uri.replace("file:///", "").replace("/", "\\") if sys.platform == "win32" else uri.replace("file://", "")
            results.append(f"- {clean_path}:{tgt_line}:{tgt_col}")

        return "Definition(s) found:\n" + "\n".join(results)
    except Exception as e:
        return f"Error querying definition: {e}"


@mcp.tool()
def clangd_find_references(file_path: str, line: int, character: int, include_declaration: bool = True) -> str:
    """
    Find all references / usages of a C/C++ symbol across the entire codebase.

    Args:
        file_path: Absolute or workspace-relative path to the source/header file.
        line: 1-indexed line number of the symbol.
        character: 1-indexed column/character position of the symbol.
        include_declaration: Whether to include the symbol's initial declaration in results.
    """
    p = _resolve_file(file_path)
    if not p.exists():
        return f"Error: File not found: {p}"

    _lsp_client.open_document_if_needed(p)
    try:
        res = _lsp_client._send_request("textDocument/references", {
            "textDocument": {"uri": p.as_uri()},
            "position": {"line": max(0, line - 1), "character": max(0, character - 1)},
            "context": {"includeDeclaration": include_declaration}
        })
        if not res:
            return "No references found."

        results = []
        for item in res:
            uri = item.get("uri", "")
            start = item.get("range", {}).get("start", {})
            tgt_line = start.get("line", 0) + 1
            tgt_col = start.get("character", 0) + 1
            clean_path = uri.replace("file:///", "").replace("/", "\\") if sys.platform == "win32" else uri.replace("file://", "")
            results.append(f"- {clean_path}:{tgt_line}:{tgt_col}")

        return f"Found {len(results)} reference(s):\n" + "\n".join(results[:100])
    except Exception as e:
        return f"Error finding references: {e}"


@mcp.tool()
def clangd_get_hover(file_path: str, line: int, character: int) -> str:
    """
    Retrieve documentation, type signatures, and evaluated macro expansions for a symbol.

    Args:
        file_path: Absolute or workspace-relative path to the source/header file.
        line: 1-indexed line number.
        character: 1-indexed column/character position.
    """
    p = _resolve_file(file_path)
    if not p.exists():
        return f"Error: File not found: {p}"

    _lsp_client.open_document_if_needed(p)
    try:
        res = _lsp_client._send_request("textDocument/hover", {
            "textDocument": {"uri": p.as_uri()},
            "position": {"line": max(0, line - 1), "character": max(0, character - 1)}
        })
        if not res:
            return "No hover information available."

        contents = res.get("contents", "")
        if isinstance(contents, dict):
            return contents.get("value", "")
        elif isinstance(contents, list):
            return "\n\n".join([c.get("value", "") if isinstance(c, dict) else str(c) for c in contents])
        return str(contents)
    except Exception as e:
        return f"Error getting hover: {e}"


@mcp.tool()
def clangd_workspace_symbol(query: str) -> str:
    """
    Fuzzy search for symbols (functions, structs, typedefs, macros) across the workspace.

    Args:
        query: Symbol name or substring to search for.
    """
    try:
        res = _lsp_client._send_request("workspace/symbol", {"query": query})
        if not res:
            return f"No symbols found matching '{query}'."

        results = []
        for sym in res[:50]:
            name = sym.get("name", "")
            kind = sym.get("kind", 0)
            container = sym.get("containerName", "")
            loc = sym.get("location", {})
            uri = loc.get("uri", "")
            line = loc.get("range", {}).get("start", {}).get("line", 0) + 1
            clean_path = uri.replace("file:///", "").replace("/", "\\") if sys.platform == "win32" else uri.replace("file://", "")
            parent_str = f" in {container}" if container else ""
            results.append(f"- [{name}] (Kind: {kind}){parent_str} -> {clean_path}:{line}")

        return f"Found {len(results)} symbol(s) matching '{query}':\n" + "\n".join(results)
    except Exception as e:
        return f"Error searching workspace symbols: {e}"


@mcp.tool()
def clangd_document_symbols(file_path: str) -> str:
    """
    Return the structural outline (classes, functions, fields, enums) of a C/C++ source file.

    Args:
        file_path: Absolute or workspace-relative path to the file.
    """
    p = _resolve_file(file_path)
    if not p.exists():
        return f"Error: File not found: {p}"

    _lsp_client.open_document_if_needed(p)
    try:
        res = _lsp_client._send_request("textDocument/documentSymbol", {
            "textDocument": {"uri": p.as_uri()}
        })
        if not res:
            return f"No symbols found in {p.name}."

        lines = []
        def parse_symbols(syms, depth=0):
            indent = "  " * depth
            for s in syms:
                name = s.get("name", "")
                detail = s.get("detail", "")
                detail_str = f" ({detail})" if detail else ""
                rg = s.get("range") or s.get("location", {}).get("range", {})
                line_no = rg.get("start", {}).get("line", 0) + 1
                lines.append(f"{indent}- Line {line_no:4d}: {name}{detail_str}")
                if "children" in s:
                    parse_symbols(s["children"], depth + 1)

        parse_symbols(res)
        return f"Document outline for {p.name}:\n" + "\n".join(lines[:150])
    except Exception as e:
        return f"Error retrieving document symbols: {e}"


@mcp.tool()
def clangd_get_diagnostics(file_path: str) -> str:
    """
    Retrieve active compiler warnings, errors, and clang-tidy lints for a file.

    Args:
        file_path: Absolute or workspace-relative path to the file.
    """
    p = _resolve_file(file_path)
    if not p.exists():
        return f"Error: File not found: {p}"

    _lsp_client.open_document_if_needed(p)
    time.sleep(0.3)  # Brief wait for clangd to publish diagnostics

    diags = _lsp_client.get_diagnostics_for_uri(p.as_uri())
    if not diags:
        return f"No diagnostics / compiler issues reported for {p.name}."

    results = []
    severity_map = {1: "ERROR", 2: "WARNING", 3: "INFO", 4: "HINT"}
    for d in diags:
        sev = severity_map.get(d.get("severity", 1), "NOTE")
        msg = d.get("message", "")
        start = d.get("range", {}).get("start", {})
        line = start.get("line", 0) + 1
        col = start.get("character", 0) + 1
        source = d.get("source", "clang")
        results.append(f"[{sev}] Line {line}:{col} ({source}): {msg}")

    return f"Diagnostics for {p.name} ({len(results)} item(s)):\n" + "\n".join(results)


@mcp.tool()
def clangd_status() -> str:
    """
    Check the operational status of the clangd LSP server process and active compilation database.
    """
    status = "RUNNING" if (_lsp_client.process and _lsp_client.process.poll() is None) else "STOPPED"
    comp_dir = str(_lsp_client.compile_commands_dir) if _lsp_client.compile_commands_dir else "None (Auto-discovery failed)"
    return (
        f"Clangd LSP Server Status:\n"
        f"- Process Status:       {status}\n"
        f"- Clangd Executable:    {_lsp_client.clangd_bin}\n"
        f"- Workspace Root:       {_lsp_client.workspace_root}\n"
        f"- Compilation Database: {comp_dir}\n"
        f"- Open Documents:       {len(_lsp_client._open_documents)}\n"
        f"- Log File:             {LOG_FILE}"
    )


if __name__ == "__main__":
    logger.info("Starting Clangd LSP FastMCP Bridge Server on stdio...")
    mcp.run(transport="stdio")
