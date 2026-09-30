#!/usr/bin/env python3
"""
ESP-IDF Build & Size Harness MCP Server.
Provides structured execution of idf.py build, idf.py reconfigure, and idf.py size
with line-numbered error extraction for agent self-correction.
"""

import sys
import logging
import os
import subprocess
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Oversight File & Stream Logging Setup
LOG_DIR = Path.home() / ".mcp_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "idf_build_mcp_server.log"

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

mcp = FastMCP("IDF-Build-Server")

DEFAULT_PROJECT_ROOT = Path(os.environ.get("BSP_BUILD_ROOT", r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\examples\Peripherals_Test_Suite")).resolve()


def _get_project_root(project_path: str = "") -> Path:
    if project_path:
        p = Path(project_path).resolve()
        if p.exists():
            return p
    return DEFAULT_PROJECT_ROOT


def _filter_errors(build_log: str) -> list[str]:
    lines = build_log.splitlines()
    error_lines = [ln for ln in lines if "error:" in ln.lower() or "fatal error" in ln.lower() or "undefined reference" in ln.lower()]
    return error_lines[:30]


@mcp.tool()
def trigger_idf_build(project_path: str = "", target: str = "esp32s3") -> dict:
    """Executes 'idf.py build' on the target ESP32-S3 BSP or user application repository.
    Returns build status, pass/fail state, and line-numbered compiler error diagnostics.
    """
    root = _get_project_root(project_path)
    if not (root / "CMakeLists.txt").exists():
        return {"status": "error", "message": f"No CMakeLists.txt found in project root {root}."}

    cmd = ["idf.py", "build"]
    res = subprocess.run(cmd, cwd=root, capture_output=True, text=True, shell=True)

    if res.returncode == 0:
        return {
            "status": "success",
            "message": "IDF build completed cleanly with exit code 0.",
            "stdout_summary": res.stdout[-1000:]
        }

    errors = _filter_errors(res.stdout + "\n" + res.stderr)
    return {
        "status": "build_error",
        "message": "IDF compilation failed.",
        "diagnostics": "\n".join(errors) if errors else (res.stderr or res.stdout)[-2000:],
        "returncode": res.returncode
    }


@mcp.tool()
def get_idf_size(project_path: str = "") -> dict:
    """Executes 'idf.py size' to return component-by-component memory size breakdown."""
    root = _get_project_root(project_path)
    cmd = ["idf.py", "size"]
    res = subprocess.run(cmd, cwd=root, capture_output=True, text=True, shell=True)

    if res.returncode == 0:
        return {
            "status": "success",
            "size_output": res.stdout
        }

    return {
        "status": "error",
        "message": f"idf.py size failed: {res.stderr}"
    }


@mcp.tool()
def reconfigure_idf_project(project_path: str = "") -> dict:
    """Executes 'idf.py reconfigure' to force CMake re-generation."""
    root = _get_project_root(project_path)
    cmd = ["idf.py", "reconfigure"]
    res = subprocess.run(cmd, cwd=root, capture_output=True, text=True, shell=True)

    return {
        "status": "success" if res.returncode == 0 else "error",
        "output": res.stdout if res.returncode == 0 else res.stderr
    }


if __name__ == "__main__":
    mcp.run()
