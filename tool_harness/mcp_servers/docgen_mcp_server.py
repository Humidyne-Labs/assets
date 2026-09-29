#!/usr/bin/env python3
"""
Doxygen & Moxygen Documentation Maintenance MCP Server.
Executes Doxygen and Moxygen documentation builds against Doxyfile in the BSP project,
matching exact build tasks from .vscode/tasks.json.
"""

import os
import shutil
import subprocess
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DocGen-Server")

DEFAULT_PROJECT_ROOT = Path(os.environ.get("BSP_ROOT", r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp")).resolve()
DOXYGEN_BIN = r"C:\Program Files\doxygen\bin\doxygen.exe"


def _get_project_root(project_path: str = "") -> Path:
    if project_path:
        p = Path(project_path).resolve()
        if p.exists():
            return p
    return DEFAULT_PROJECT_ROOT


@mcp.tool()
def generate_api_docs(mode: str = "full", project_path: str = "") -> dict:
    """Runs Doxygen and Moxygen documentation generation matching workspace tasks.json.

    Args:
        mode: Documentation build mode:
            - 'full': Doxygen + Moxygen single-page API ref ('moxygen --flavor github -a -o docs/api.md docs/doxygen/xml')
            - 'multi': Doxygen + Moxygen multi-page API ref ('moxygen --flavor github -a -g -c -o docs/api/%s.md docs/doxygen/xml')
            - 'doxygen_only': Run Doxygen build only
            - 'moxygen_only': Run Moxygen markdown conversion from existing XML
        project_path: Target repository root containing Doxyfile (default esp32-s3_bsp root).
    """
    root = _get_project_root(project_path)
    doxyfile = root / "Doxyfile"
    if not doxyfile.exists():
        return {"status": "error", "message": f"Doxyfile not found in project root {root}."}

    env = os.environ.copy()
    env["PATH"] = r"C:\Program Files\doxygen\bin;C:\Program Files (x86)\doxygen\bin;" + env.get("PATH", "")

    logs = []

    # 1. Run Doxygen if required
    if mode in ("full", "multi", "doxygen_only"):
        dox_cmd = [DOXYGEN_BIN if os.path.exists(DOXYGEN_BIN) else "doxygen", "Doxyfile"]
        res_dox = subprocess.run(dox_cmd, cwd=root, capture_output=True, text=True, env=env)
        logs.append(f"--- Doxygen Output ---\n{res_dox.stdout}\n{res_dox.stderr}")

        if res_dox.returncode != 0:
            return {
                "status": "error",
                "message": "Doxygen execution failed.",
                "diagnostics": res_dox.stderr or res_dox.stdout
            }

    if mode == "doxygen_only":
        return {
            "status": "success",
            "message": "Doxygen documentation built successfully into docs/doxygen/.",
            "log": "\n".join(logs)
        }

    # 2. Run Moxygen if required
    xml_dir = root / "docs" / "doxygen" / "xml"
    if not xml_dir.exists():
        return {
            "status": "error",
            "message": f"Doxygen XML directory not found at {xml_dir}. Run Doxygen first."
        }

    if mode == "multi":
        api_dir = root / "docs" / "api"
        api_dir.mkdir(parents=True, exist_ok=True)
        mox_cmd = ["moxygen", "--flavor", "github", "-a", "-g", "-c", "-o", "docs/api/%s.md", "docs/doxygen/xml"]
    else:  # full or moxygen_only
        (root / "docs").mkdir(parents=True, exist_ok=True)
        mox_cmd = ["moxygen", "--flavor", "github", "-a", "-o", "docs/api.md", "docs/doxygen/xml"]

    res_mox = subprocess.run(mox_cmd, cwd=root, capture_output=True, text=True, shell=True, env=env)
    logs.append(f"--- Moxygen Output ---\n{res_mox.stdout}\n{res_mox.stderr}")

    if res_mox.returncode != 0:
        return {
            "status": "error",
            "message": "Moxygen execution failed. Ensure moxygen NPM package is installed.",
            "diagnostics": res_mox.stderr or res_mox.stdout
        }

    output_file = "docs/api/%s.md" if mode == "multi" else "docs/api.md"
    return {
        "status": "success",
        "message": f"API Markdown documentation successfully generated at {output_file}.",
        "logs": "\n".join(logs)
    }


@mcp.tool()
def clean_generated_docs(project_path: str = "") -> dict:
    """Cleans all generated documentation outputs (docs/doxygen, docs/api.md, docs/api)."""
    root = _get_project_root(project_path)
    docs_dir = root / "docs"

    removed = []
    dox_dir = docs_dir / "doxygen"
    if dox_dir.exists():
        shutil.rmtree(dox_dir)
        removed.append("docs/doxygen/")

    api_md = docs_dir / "api.md"
    if api_md.exists():
        api_md.unlink()
        removed.append("docs/api.md")

    api_dir = docs_dir / "api"
    if api_dir.exists():
        shutil.rmtree(api_dir)
        removed.append("docs/api/")

    return {
        "status": "success",
        "message": f"Cleaned generated documentation: {', '.join(removed) if removed else 'None found.'}"
    }


if __name__ == "__main__":
    mcp.run()
