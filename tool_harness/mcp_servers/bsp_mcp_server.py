#!/usr/bin/env python3
"""
ESP32-S3 BSP Source Files & Examples MCP Server.
Provides targeted search, header discovery, API signature lookup, and example retrieval
for the ESP32-S3 Board Support Package (BSP).
"""

import sys
import logging
import os
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Oversight File & Stream Logging Setup
LOG_DIR = Path.home() / ".mcp_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "bsp_mcp_server.log"

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

mcp = FastMCP("ESP32-S3-BSP-Server")

# Resolve BSP root from environment variable or default system path
DEFAULT_BSP_ROOT = Path(os.environ.get("BSP_ROOT", r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp")).resolve()


def _get_bsp_root() -> Path:
    return DEFAULT_BSP_ROOT


def _find_bsp_include_dir() -> Path:
    root = _get_bsp_root()
    candidates = [
        root / "components" / "esp32-s3_bsp" / "include" / "bsp",
        root / "components" / "esp32-s3_bsp" / "include",
        root / "components" / "bsp" / "include",
        root / "include",
        root,
    ]
    for c in candidates:
        if c.exists() and list(c.glob("*.h")):
            return c
    return root


def _find_bsp_src_dir() -> Path:
    root = _get_bsp_root()
    candidates = [
        root / "components" / "esp32-s3_bsp" / "src",
        root / "components" / "bsp" / "src",
        root / "src",
        root,
    ]
    for c in candidates:
        if c.exists() and list(c.glob("*.c")):
            return c
    return root


def _find_bsp_examples_dir() -> Path:
    root = _get_bsp_root()
    candidates = [
        root / "examples",
        root / "components" / "esp32-s3_bsp" / "examples",
    ]
    for c in candidates:
        if c.exists():
            return c
    return root / "examples"


@mcp.tool()
def list_bsp_headers_and_sources() -> dict:
    """Lists all available header files (*.h), source files (*.c), and pinout definitions in the BSP."""
    root = _get_bsp_root()
    if not root.exists():
        return {"error": f"BSP root directory not found at {root}"}

    include_dir = _find_bsp_include_dir()
    src_dir = _find_bsp_src_dir()
    examples_dir = _find_bsp_examples_dir()

    headers = [str(f.relative_to(root)) for f in include_dir.rglob("*.h")] if include_dir.exists() else []
    sources = [str(f.relative_to(root)) for f in src_dir.rglob("*.c")] if src_dir.exists() else []
    examples = [str(f.relative_to(root)) for f in examples_dir.rglob("*") if f.suffix in (".c", ".h", ".md")] if examples_dir.exists() else []

    return {
        "bsp_root": str(root),
        "headers": sorted(headers),
        "sources": sorted(sources),
        "examples": sorted(examples),
    }


@mcp.tool()
def read_bsp_header(header_name: str) -> str:
    """Reads the complete contents of a specific BSP header file (e.g. 'pinout.h', 'bsp_display.h', 'bsp_i2c.h')."""
    include_dir = _find_bsp_include_dir()
    root = _get_bsp_root()

    target = include_dir / header_name
    if not target.exists():
        matches = list(root.rglob(header_name))
        if matches:
            target = matches[0]

    if not target.exists() or not target.is_file():
        return f"Error: Header file '{header_name}' not found under BSP root {root}."

    return f"/* === Header: {target.relative_to(root)} === */\n\n" + target.read_text(encoding="utf-8", errors="ignore")


@mcp.tool()
def read_bsp_source(source_name: str) -> str:
    """Reads the complete contents of a specific BSP C implementation source file (e.g. 'bsp_display.c', 'bsp_i2c.c')."""
    src_dir = _find_bsp_src_dir()
    root = _get_bsp_root()

    target = src_dir / source_name
    if not target.exists():
        matches = list(root.rglob(source_name))
        if matches:
            target = matches[0]

    if not target.exists() or not target.is_file():
        return f"Error: Source file '{source_name}' not found under BSP root {root}."

    return f"/* === Source: {target.relative_to(root)} === */\n\n" + target.read_text(encoding="utf-8", errors="ignore")


@mcp.tool()
def search_bsp_api(query: str) -> list[dict]:
    """Searches for function prototypes, macros, enums, or pin definitions matching a keyword across all BSP headers and sources."""
    root = _get_bsp_root()
    if not root.exists():
        return [{"error": f"BSP root directory not found at {root}"}]

    results = []
    query_lower = query.lower()

    for file_path in root.rglob("*"):
        if file_path.suffix in (".h", ".c") and file_path.is_file():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                for line_num, line in enumerate(lines, 1):
                    if query_lower in line.lower():
                        results.append({
                            "file": str(file_path.relative_to(root)),
                            "line": line_num,
                            "content": line.strip()
                        })
                        if len(results) >= 30:
                            return results
            except Exception:
                continue

    return results


@mcp.tool()
def list_bsp_examples() -> list[str]:
    """Lists all reference example files available in the BSP examples directory."""
    examples_dir = _find_bsp_examples_dir()
    root = _get_bsp_root()
    if not examples_dir.exists():
        return [f"Examples directory not found at {examples_dir}"]

    return [
        str(f.relative_to(root))
        for f in sorted(examples_dir.rglob("*"))
        if f.is_file() and f.suffix in (".c", ".h", ".md", ".txt")
    ]


@mcp.tool()
def get_bsp_example_code(example_relative_path: str) -> str:
    """Reads the complete source code of a specific BSP reference example (accepts project folder name or direct file path)."""
    root = _get_bsp_root()
    examples_dir = _find_bsp_examples_dir()

    candidates = [
        root / example_relative_path,
        examples_dir / example_relative_path,
        examples_dir / f"{example_relative_path}_example",
        examples_dir / example_relative_path / "main" / "main.c",
        examples_dir / f"{example_relative_path}_example" / "main" / "main.c",
    ]

    target = None
    for cand in candidates:
        if cand.exists():
            if cand.is_file():
                target = cand
                break
            elif cand.is_dir():
                main_c = cand / "main" / "main.c"
                if main_c.exists() and main_c.is_file():
                    target = main_c
                    break

    if not target or not target.is_file():
        return f"Error: Example file or project '{example_relative_path}' not found."

    display_path = str(target.relative_to(root)) if root in target.parents or target.parent == root else str(target)
    return f"/* === BSP Example: {display_path} === */\n\n" + target.read_text(encoding="utf-8", errors="ignore")


if __name__ == "__main__":
    mcp.run()
