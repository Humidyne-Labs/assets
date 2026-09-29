#!/usr/bin/env python3
"""
Firmware Static Memory Footprint & Map File Analyzer MCP Server.
Parses ESP-IDF build map files and size reports to calculate DRAM, IRAM, DIRAM, PSRAM,
and Flash memory usage per component and symbol.
"""

import os
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Firmware-Analyzer-Server")

DEFAULT_PROJECT_ROOT = Path(os.environ.get("BSP_BUILD_ROOT", r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\examples\Peripherals_Test_Suite")).resolve()


def _find_build_dir(project_path: str = "") -> Path:
    if project_path:
        p = Path(project_path).resolve()
        if (p / "build").exists():
            return p / "build"
        if p.name == "build" and p.exists():
            return p
    default_build = DEFAULT_PROJECT_ROOT / "build"
    if default_build.exists():
        return default_build
    return default_build


@mcp.tool()
def get_memory_usage_summary(project_path: str = "") -> dict:
    """Parses the target ESP-IDF build directory to report total Flash, IRAM, DRAM, and PSRAM memory footprint."""
    build_dir = _find_build_dir(project_path)
    if not build_dir.exists():
        return {"error": f"Build directory not found at {build_dir}. Run 'idf.py build' first."}

    map_files = list(build_dir.rglob("*.map"))
    if not map_files:
        return {"error": f"No .map file found under build directory {build_dir}."}

    target_map = map_files[0]
    map_text = target_map.read_text(encoding="utf-8", errors="ignore")

    # Extract memory section statistics
    sections = {
        "iram": 0,
        "dram_data": 0,
        "dram_bss": 0,
        "flash_code": 0,
        "flash_rodata": 0,
        "psram": 0,
    }

    for line in map_text.splitlines():
        # Example linker section summaries
        m_iram = re.search(r"\.iram0\.text\s+0x[0-9a-fA-F]+\s+0x([0-9a-fA-F]+)", line)
        if m_iram:
            sections["iram"] += int(m_iram.group(1), 16)

        m_ddata = re.search(r"\.dram0\.data\s+0x[0-9a-fA-F]+\s+0x([0-9a-fA-F]+)", line)
        if m_ddata:
            sections["dram_data"] += int(m_ddata.group(1), 16)

        m_dbss = re.search(r"\.dram0\.bss\s+0x[0-9a-fA-F]+\s+0x([0-9a-fA-F]+)", line)
        if m_dbss:
            sections["dram_bss"] += int(m_dbss.group(1), 16)

        m_ftext = re.search(r"\.flash\.text\s+0x[0-9a-fA-F]+\s+0x([0-9a-fA-F]+)", line)
        if m_ftext:
            sections["flash_code"] += int(m_ftext.group(1), 16)

        m_frodata = re.search(r"\.flash\.rodata\s+0x[0-9a-fA-F]+\s+0x([0-9a-fA-F]+)", line)
        if m_frodata:
            sections["flash_rodata"] += int(m_frodata.group(1), 16)

    total_dram = sections["dram_data"] + sections["dram_bss"]
    total_flash = sections["flash_code"] + sections["flash_rodata"]

    return {
        "build_dir": str(build_dir),
        "map_file": str(target_map.name),
        "memory_summary_bytes": {
            "iram_bytes": sections["iram"],
            "dram_total_bytes": total_dram,
            "dram_data_bytes": sections["dram_data"],
            "dram_bss_bytes": sections["dram_bss"],
            "flash_code_bytes": sections["flash_code"],
            "flash_rodata_bytes": sections["flash_rodata"],
            "flash_total_bytes": total_flash,
        },
        "memory_summary_human": {
            "iram": f"{sections['iram'] / 1024:.2f} KB",
            "dram": f"{total_dram / 1024:.2f} KB",
            "flash": f"{total_flash / 1024:.2f} KB ({total_flash / (1024*1024):.2f} MB)",
        }
    }


@mcp.tool()
def analyze_top_symbols(project_path: str = "", limit: int = 25) -> list[dict]:
    """Parses the build .map file to return the largest functions and static variables consuming Flash or RAM."""
    build_dir = _find_build_dir(project_path)
    if not build_dir.exists():
        return [{"error": f"Build directory not found at {build_dir}"}]

    map_files = list(build_dir.rglob("*.map"))
    if not map_files:
        return [{"error": f"No .map file found under build directory {build_dir}"}]

    target_map = map_files[0]
    map_text = target_map.read_text(encoding="utf-8", errors="ignore")

    symbols = []
    # Match standard map file symbol entries: address size symbol_name object_file
    pattern = re.compile(r"0x[0-9a-fA-F]+\s+0x([0-9a-fA-F]+)\s+([\w\.\$]+)\s+(.+)")

    for line in map_text.splitlines():
        match = pattern.search(line)
        if match:
            size_hex, sym_name, origin = match.groups()
            try:
                size_bytes = int(size_hex, 16)
                if size_bytes > 32 and not sym_name.startswith("."):
                    symbols.append({
                        "symbol": sym_name,
                        "size_bytes": size_bytes,
                        "size_human": f"{size_bytes} bytes ({size_bytes / 1024:.2f} KB)",
                        "origin": origin.strip()
                    })
            except ValueError:
                continue

    sorted_symbols = sorted(symbols, key=lambda x: x["size_bytes"], reverse=True)
    return sorted_symbols[:limit]


if __name__ == "__main__":
    mcp.run()
