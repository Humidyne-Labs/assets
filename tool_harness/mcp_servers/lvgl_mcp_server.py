#!/usr/bin/env python3
"""
LVGL Documentation and Example Provider MCP Server.
Points to LVGL 9 repository root (lvgl-9.6.0) to provide header inspection,
API symbol lookup, widget documentation, and reference examples.
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
LOG_FILE = LOG_DIR / "lvgl_mcp_server.log"

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

mcp = FastMCP("LVGL-Context-Server")

# Resolve LVGL root from environment variable or default harness directory
HARNESS_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LVGL_ROOT = Path(os.environ.get("LVGL_ROOT", HARNESS_DIR / "lvgl-9.6.0")).resolve()


def _get_lvgl_root() -> Path:
    if DEFAULT_LVGL_ROOT.exists():
        return DEFAULT_LVGL_ROOT
    # Fallback search for any lvgl-9.* folder in harness dir
    candidates = list(HARNESS_DIR.glob("lvgl-9*")) + list(HARNESS_DIR.glob("lvgl*"))
    if candidates:
        return candidates[0]
    return DEFAULT_LVGL_ROOT


def _find_header_files() -> list[Path]:
    root = _get_lvgl_root()
    src_dir = root / "src"
    if not src_dir.exists():
        return list(root.rglob("*.h"))
    return list(src_dir.rglob("*.h")) + list(root.glob("*.h"))


@mcp.tool()
def get_lvgl_version() -> str:
    """Check the exact major, minor, and patch version of the active LVGL repository.
    Always call this first to prevent mixing LVGL v8 and v9 function calls.
    """
    root = _get_lvgl_root()
    if not root.exists():
        return f"Error: LVGL root path not found at {root}"

    candidates = list(root.rglob("lv_version.h")) + [root / "lvgl.h"]
    for path in candidates:
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="ignore")
            major = re.search(r"#define\s+LVGL_VERSION_MAJOR\s+(\d+)", text)
            minor = re.search(r"#define\s+LVGL_VERSION_MINOR\s+(\d+)", text)
            patch = re.search(r"#define\s+LVGL_VERSION_PATCH\s+(\d+)", text)
            if major and minor and patch:
                return (
                    f"LVGL Version: {major.group(1)}.{minor.group(1)}.{patch.group(1)}\n"
                    f"Path: {path}"
                )

    return f"LVGL repository detected at {root}, but version macro definitions could not be parsed."


@mcp.tool()
def search_lvgl_api(function_or_type: str) -> str:
    """Find the exact function prototype, parameter list, and Doxygen docstring
    for any LVGL API symbol (e.g., 'lv_label_set_text', 'lv_obj_add_event_cb', 'lv_display_create').
    """
    root = _get_lvgl_root()
    if not root.exists():
        return f"Error: LVGL root path not found at {root}"

    headers = _find_header_files()
    pattern = re.compile(
        rf"(/\*\*[\s\S]*?\*/\s*(?:static\s+inline\s+)?[\w\*\s]+\b{re.escape(function_or_type)}\b\s*\([^;]*\);)",
        re.MULTILINE,
    )

    matches = []
    for h in headers:
        try:
            content = h.read_text(encoding="utf-8", errors="ignore")
            if function_or_type in content:
                found = pattern.findall(content)
                for f in found:
                    rel_path = h.relative_to(root)
                    matches.append(f"// Defined in: {rel_path}\n{f.strip()}")
        except Exception:
            continue

    if matches:
        return "\n\n".join(matches[:5])

    return f"Symbol '{function_or_type}' not found across {len(headers)} header files."


@mcp.tool()
def get_widget_api(widget_name: str) -> str:
    """Retrieve all public functions and configuration definitions for a specific widget.
    Example widget_name: 'button', 'btn', 'label', 'slider', 'roller', 'chart', 'image', 'arc', 'bar'.
    """
    root = _get_lvgl_root()
    headers = _find_header_files()
    clean_name = widget_name.lower().replace("lv_", "")
    target_headers = [h for h in headers if clean_name in h.name.lower()]

    if not target_headers:
        return f"No header file matching widget '{widget_name}' found."

    results = []
    for h in target_headers:
        rel_path = h.relative_to(root)
        lines = h.read_text(encoding="utf-8", errors="ignore").splitlines()

        sig_lines = []
        capture = False
        for line in lines:
            if "/**" in line or line.startswith("typedef enum"):
                capture = True
            if capture:
                sig_lines.append(line)
            if ";" in line and capture and not line.startswith(" *"):
                capture = False

        results.append(f"/* === {rel_path} === */\n" + "\n".join(sig_lines[:250]))

    return "\n\n".join(results)


@mcp.tool()
def search_lvgl_examples(keyword: str) -> list[str]:
    """Search for relevant official LVGL reference examples.
    Example keywords: 'button', 'event', 'flex', 'grid', 'meter', 'anim', 'label'.
    Returns relative paths of matching example C files.
    """
    root = _get_lvgl_root()
    examples_dir = root / "examples"
    if not examples_dir.exists():
        return [f"Error: 'examples/' directory not found in LVGL root ({root})."]

    matches = []
    for c_file in examples_dir.rglob("*.c"):
        if keyword.lower() in c_file.name.lower() or keyword.lower() in str(c_file.parent).lower():
            matches.append(str(c_file.relative_to(root)))

    return sorted(matches)[:15]


@mcp.tool()
def get_lvgl_example_code(example_relative_path: str) -> str:
    """Read the full source code of an official LVGL reference example.
    Pass a path returned by search_lvgl_examples (e.g., 'examples/widgets/button/lv_example_button_1.c').
    """
    root = _get_lvgl_root()
    target = root / example_relative_path
    if not target.exists() or not target.is_file():
        return f"Error: Example file not found at {example_relative_path} under {root}"

    return target.read_text(encoding="utf-8", errors="ignore")


if __name__ == "__main__":
    mcp.run()
