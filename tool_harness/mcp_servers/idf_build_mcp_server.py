#!/usr/bin/env python3
"""
ESP-IDF Build & Size Harness MCP Server.
Provides structured execution of idf.py build, idf.py reconfigure, and idf.py size
with line-numbered error extraction for agent self-correction.
Automatically exports and manages ESP-IDF environment variables (IDF_PATH, toolchains, python virtualenv).
"""

import sys
import logging
import os
import json
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
_IDF_ENV: dict | None = None


def _discover_export_script(custom_export_path: str = "", custom_idf_path: str = "") -> Path | None:
    # 1. Custom explicit export script path
    if custom_export_path:
        p = Path(custom_export_path).resolve()
        if p.exists():
            return p

    # 2. Custom IDF directory path
    if custom_idf_path:
        p_idf = Path(custom_idf_path).resolve()
        for ext in ("export.bat", "export.ps1", "export.sh"):
            if (p_idf / ext).exists():
                return p_idf / ext

    # 3. Existing IDF_PATH environment variable
    idf_path_env = os.environ.get("IDF_PATH")
    if idf_path_env:
        p_env = Path(idf_path_env).resolve()
        for ext in ("export.bat", "export.ps1", "export.sh"):
            if (p_env / ext).exists():
                return p_env / ext

    # 4. ~/.espressif/idf-env.json configuration
    idf_env_json = Path.home() / ".espressif" / "idf-env.json"
    if idf_env_json.exists():
        try:
            data = json.loads(idf_env_json.read_text(encoding="utf-8"))
            installed = data.get("idfInstalled", {})
            for key, info in installed.items():
                p_str = info.get("path") or key
                if p_str:
                    p_installed = Path(p_str).resolve()
                    for ext in ("export.bat", "export.ps1", "export.sh"):
                        if (p_installed / ext).exists():
                            return p_installed / ext
        except Exception:
            pass

    # 5. Fallback candidate paths
    candidates = [
        Path(r"C:\esp\v6.1\esp-idf\export.bat"),
        Path(r"C:\esp\v5.3\esp-idf\export.bat"),
        Path(r"C:\esp\v5.1\esp-idf\export.bat"),
        Path(r"C:\Espressif\frameworks\esp-idf\export.bat"),
        Path.home() / "esp" / "esp-idf" / "export.sh",
        Path(r"C:\esp-idf\export.bat"),
    ]
    for c in candidates:
        if c.exists():
            return c

    return None


@mcp.tool()
def init_idf_environment(export_script_path: str = "", idf_path: str = "") -> dict:
    """Initializes and exports ESP-IDF environment variables (IDF_PATH, toolchain paths, python venv).
    Call this tool to manually set up ESP-IDF environment or to point to a specific ESP-IDF export script.

    Args:
        export_script_path: Optional path to export.bat / export.ps1 / export.sh.
        idf_path: Optional path to ESP-IDF root folder containing export script.
    """
    global _IDF_ENV
    script = _discover_export_script(export_script_path, idf_path)
    if not script or not script.exists():
        return {
            "status": "error",
            "message": "Could not locate ESP-IDF export script (export.bat / export.sh). Please specify export_script_path."
        }

    env_map = os.environ.copy()

    if sys.platform == "win32":
        cmd = f'cmd.exe /c "call \"{script}\" > NUL && set"'
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True, env=env_map)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    env_map[k] = v
                    os.environ[k] = v
    else:
        cmd = f'bash -c "source \"{script}\" > /dev/null && env"'
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True, env=env_map)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    env_map[k] = v
                    os.environ[k] = v

    _IDF_ENV = env_map

    # Check toolchain availability in exported PATH
    path_entries = [Path(p) for p in env_map.get("PATH", "").split(os.pathsep) if p.strip()]
    toolchain_found = any(
        (p / "xtensa-esp32s3-elf-gcc.exe").exists() or (p / "xtensa-esp32s3-elf-gcc").exists() or (p / "ninja.exe").exists() or (p / "ninja").exists()
        for p in path_entries
    )

    return {
        "status": "success",
        "message": f"Successfully exported ESP-IDF environment variables from {script}.",
        "export_script": str(script),
        "idf_path": env_map.get("IDF_PATH"),
        "idf_target": env_map.get("IDF_TARGET", "esp32s3"),
        "toolchain_ready": toolchain_found
    }


@mcp.tool()
def get_idf_environment_status() -> dict:
    """Checks the current initialization state of the ESP-IDF environment variables, toolchains, and path configuration."""
    is_exported = bool(os.environ.get("IDF_PATH"))
    script = _discover_export_script()

    path_entries = [Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p.strip()]
    toolchain_found = any(
        (p / "xtensa-esp32s3-elf-gcc.exe").exists() or (p / "xtensa-esp32s3-elf-gcc").exists() or (p / "ninja.exe").exists() or (p / "ninja").exists()
        for p in path_entries
    )

    return {
        "is_initialized": is_exported and toolchain_found,
        "idf_path": os.environ.get("IDF_PATH"),
        "discovered_export_script": str(script) if script else None,
        "toolchain_ready": toolchain_found,
        "env_vars_count": len(os.environ)
    }


def _ensure_env() -> dict:
    """Ensures ESP-IDF environment is exported into os.environ before executing idf.py commands."""
    global _IDF_ENV
    if _IDF_ENV is None or "IDF_PATH" not in os.environ:
        init_idf_environment()
    return _IDF_ENV or os.environ.copy()


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
    Automatically initializes ESP-IDF environment variables before compilation if not yet set up.
    Returns build status, pass/fail state, and line-numbered compiler error diagnostics.
    """
    env_map = _ensure_env()
    root = _get_project_root(project_path)
    if not (root / "CMakeLists.txt").exists():
        return {"status": "error", "message": f"No CMakeLists.txt found in project root {root}."}

    cmd = ["idf.py", "build"]
    res = subprocess.run(cmd, cwd=root, capture_output=True, text=True, shell=True, env=env_map)

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
    """Executes 'idf.py size' to return component-by-component memory size breakdown.
    Automatically initializes ESP-IDF environment variables if needed.
    """
    env_map = _ensure_env()
    root = _get_project_root(project_path)
    cmd = ["idf.py", "size"]
    res = subprocess.run(cmd, cwd=root, capture_output=True, text=True, shell=True, env=env_map)

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
    """Executes 'idf.py reconfigure' to force CMake re-generation.
    Automatically initializes ESP-IDF environment variables if needed.
    """
    env_map = _ensure_env()
    root = _get_project_root(project_path)
    cmd = ["idf.py", "reconfigure"]
    res = subprocess.run(cmd, cwd=root, capture_output=True, text=True, shell=True, env=env_map)

    return {
        "status": "success" if res.returncode == 0 else "error",
        "output": res.stdout if res.returncode == 0 else res.stderr
    }


if __name__ == "__main__":
    _ensure_env()
    mcp.run()
